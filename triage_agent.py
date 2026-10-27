"""
Hostel Complaint Triage AI Agent
Powered by local Gemma 4 via Ollama
"""

import json
import logging
import re
from typing import Any, Dict, List
import os
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HostelTriageAgent")

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_API_URL = f"{OLLAMA_BASE}/api/generate"
DEFAULT_MODEL = os.environ.get("GEMMA_MODEL", "gemma4:latest")

SYSTEM_PROMPT = """You are an expert AI Hostel Operations Triage Agent.
Given a raw chat dump of student complaints, parse each complaint into a structured JSON array of objects.

Triage Rules:
1. Extract EVERY individual complaint or issue mentioned in the chat.
2. Extract the room or common area location (e.g. "B-204", "108", "Wing C Terrace"). If no room/location is mentioned, set "room": "Missing / Unknown".
3. Classify category into: "Electrical & Fire", "Plumbing & Water", "Medical & Safety", "Infrastructure & Lift", "Internet & IT", "Food & Mess", "Discipline & Noise", "Other".
4. Assign Urgency:
   - "Critical": Immediate danger to life, fire risk, live electrical shock, trapped in elevator, or high fever/vomiting medical emergency.
   - "High": Safety hazard, smoking wire, flooding, locked in room, severe disruption.
   - "Medium": Wi-Fi down, AC breakdown, loud noise, water issue.
   - "Low": Food temperature, minor maintenance, loose fan regulator, minor disputes.
5. Provide a crisp, concise "one_line_summary" (under 12 words) for 30-second warden skimming.
6. Provide a concise "action_required" (under 10 words).
7. Provide a "suggested_reply" (one short sentence for the student).

Respond ONLY with a valid JSON object in this format:
{
  "complaints": [
    {
      "id": 1,
      "student_raw": "...",
      "room": "B-204",
      "category": "Electrical & Fire",
      "urgency": "Critical",
      "urgency_reason": "Live sparks hazard",
      "one_line_summary": "B-204: Water leaking on fan switch with sparks",
      "action_required": "Cut power and send electrician",
      "suggested_reply": "Power is being disconnected. Please stay away from switch."
    }
  ]
}
"""

URGENCY_RANK = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1
}


def clean_llm_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Safely extract and parse JSON from LLM output.
    Includes a robust streaming recovery parser if output is truncated or malformed.
    """
    if not raw_text:
        return {"complaints": []}

    raw_text = raw_text.strip()
    
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
    if fence_match:
        raw_text = fence_match.group(1).strip()

    # Attempt 1: Direct JSON parse
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    # Attempt 2: Extract between outer braces or brackets
    b_start = raw_text.find("{")
    b_end = raw_text.rfind("}")
    if b_start != -1 and b_end != -1 and b_end > b_start:
        try:
            return json.loads(raw_text[b_start : b_end + 1])
        except Exception:
            pass

    arr_start = raw_text.find("[")
    arr_end = raw_text.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        try:
            items = json.loads(raw_text[arr_start : arr_end + 1])
            return {"complaints": items}
        except Exception:
            pass

    # Attempt 3: Robust incremental parser for partial/truncated JSON
    # Extracts all fully formed {...} objects within the complaints array
    complaints = []
    start_arr = raw_text.find("[")
    search_text = raw_text[start_arr + 1:] if start_arr != -1 else raw_text
    
    i = 0
    n = len(search_text)
    while i < n:
        if search_text[i] == '{':
            depth = 0
            in_str = False
            escape = False
            obj_start = i
            obj_end = -1
            j = i
            while j < n:
                char = search_text[j]
                if in_str:
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == '"':
                        in_str = False
                else:
                    if char == '"':
                        in_str = True
                    elif char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            obj_end = j
                            break
                j += 1
            if obj_end != -1:
                chunk = search_text[obj_start : obj_end + 1]
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict) and ("one_line_summary" in obj or "room" in obj or "student_raw" in obj):
                        complaints.append(obj)
                except Exception:
                    pass
                i = obj_end + 1
            else:
                break
        else:
            i += 1

    if complaints:
        logger.info(f"Recovered {len(complaints)} complaints from partial/repaired JSON response.")
        return {"complaints": complaints}

    raise ValueError(f"Unable to parse LLM response into JSON. Raw output: {raw_text[:200]}...")


def triage_hostel_chat(
    chat_dump: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_API_URL,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Takes a raw string of hostel chat messages and returns structured,
    urgency-sorted complaints for the hostel warden.
    """
    if not chat_dump or not chat_dump.strip():
        return {
            "success": False,
            "error": "No chat dump provided. Please paste student chat messages.",
            "complaints": []
        }

    full_prompt = f"{SYSTEM_PROMPT}\n\nInput Student Chat Dump:\n\"\"\"\n{chat_dump.strip()}\n\"\"\""

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 4096  # Generous token limit to prevent mid-JSON cutoffs
        }
    }

    groq_key = os.environ.get("GROQ_API_KEY")

    try:
        if groq_key:
            logger.info("Dispatching triage request to Groq Cloud (Gemma)...")
            groq_model = os.environ.get("GROQ_MODEL", "gemma2-9b-it")
            groq_payload = {
                "model": groq_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Input Student Chat Dump:\n{chat_dump.strip()}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json=groq_payload,
                timeout=timeout
            )
            res.raise_for_status()
            raw_llm_output = res.json()["choices"][0]["message"]["content"] or ""
            model_used = f"Groq Cloud ({groq_model})"
        else:
            logger.info(f"Dispatching triage request to Ollama ({model})...")
            response = requests.post(ollama_url, json=payload, timeout=timeout)
            response.raise_for_status()
            res_data = response.json()
            raw_llm_output = res_data.get("response", "")
            model_used = model

        parsed = clean_llm_json_response(raw_llm_output)

        # Normalize structure
        if isinstance(parsed, list):
            complaints = parsed
        elif isinstance(parsed, dict):
            complaints = parsed.get("complaints", parsed.get("items", []))
            if not complaints and "raw_message" in parsed:
                complaints = [parsed]
        else:
            complaints = []

        # Validate and augment each complaint
        normalized_complaints: List[Dict[str, Any]] = []
        for idx, item in enumerate(complaints, start=1):
            urgency = item.get("urgency", "Medium").title()
            if urgency not in URGENCY_RANK:
                urgency = "Medium"

            room = str(item.get("room", "Missing / Unknown")).strip()
            is_missing_room = (
                item.get("has_missing_room", False)
                or not room
                or room.lower() in ["unknown", "missing", "none", "n/a", "missing / unknown"]
            )
            if is_missing_room:
                room = "Missing / Unknown"

            normalized = {
                "id": idx,
                "student_raw": item.get("student_raw", item.get("raw_message", "")),
                "room": room,
                "has_missing_room": is_missing_room,
                "category": item.get("category", "Other"),
                "urgency": urgency,
                "urgency_rank": URGENCY_RANK.get(urgency, 2),
                "urgency_reason": item.get("urgency_reason", "Routine hostel issue reported."),
                "one_line_summary": item.get("one_line_summary", "Hostel complaint recorded."),
                "action_required": item.get("action_required", "Assign relevant staff to inspect."),
                "suggested_reply": item.get(
                    "suggested_reply",
                    "Acknowledged. Warden office has logged this request."
                    if not is_missing_room
                    else "Received your complaint. Please share your room number immediately so we can dispatch help."
                ),
            }
            normalized_complaints.append(normalized)

        # Sort complaints strictly: Critical (4) -> High (3) -> Medium (2) -> Low (1)
        normalized_complaints.sort(key=lambda x: x["urgency_rank"], reverse=True)

        # Compute summary metrics for 60-second skim header
        metrics = {
            "total": len(normalized_complaints),
            "critical": sum(1 for c in normalized_complaints if c["urgency"] == "Critical"),
            "high": sum(1 for c in normalized_complaints if c["urgency"] == "High"),
            "medium": sum(1 for c in normalized_complaints if c["urgency"] == "Medium"),
            "low": sum(1 for c in normalized_complaints if c["urgency"] == "Low"),
            "missing_room": sum(1 for c in normalized_complaints if c["has_missing_room"]),
        }

        return {
            "success": True,
            "metrics": metrics,
            "complaints": normalized_complaints,
            "model_used": model
        }

    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to Ollama server.")
        return {
            "success": False,
            "error": "Cannot connect to local Ollama server at http://127.0.0.1:11434. Please ensure Ollama is running (`ollama serve`).",
            "complaints": []
        }
    except Exception as e:
        logger.exception("Error during triage processing")
        return {
            "success": False,
            "error": f"Triage failed: {str(e)}",
            "complaints": []
        }
