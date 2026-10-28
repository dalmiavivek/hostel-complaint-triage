"""
Hostel Complaint Triage - Flask Web Application
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import uuid
import time
from flask import Flask, render_template, request, jsonify, Response, send_file
import requests
from triage_agent import triage_hostel_chat, DEFAULT_MODEL, OLLAMA_BASE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HostelApp")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_FILE = os.path.join(BASE_DIR, "sample_dumps.json")


def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("presets", [])
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
    return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """Verify Ollama connection or Groq Cloud readiness."""
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        if "gemma" in groq_model.lower():
            groq_model = "llama-3.1-8b-instant"
        return jsonify({
            "status": "online",
            "cloud": True,
            "provider": "Groq Cloud",
            "active_model": groq_model
        })

    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            model_names = [m.get("name") for m in models_data]
            has_gemma = any("gemma" in m for m in model_names)
            return jsonify({
                "status": "online",
                "ollama": True,
                "has_gemma": has_gemma,
                "models": model_names,
                "active_model": DEFAULT_MODEL
            })
    except Exception as e:
        return jsonify({
            "status": "offline",
            "ollama": False,
            "error": str(e),
            "hint": "Please ensure Ollama is running (`ollama serve`)."
        }), 503


@app.route("/api/models", methods=["GET"])
def list_models():
    """List available models for the active provider."""
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            r = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {groq_key.strip()}"},
                timeout=5
            )
            return jsonify(r.json())
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"provider": "local_ollama", "note": "Set GROQ_API_KEY to see Groq models."})


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Return pre-configured realistic hostel chat datasets for fast live demo."""
    presets = load_presets()
    return jsonify({"presets": presets})


@app.route("/api/triage", methods=["POST"])
def run_triage():
    """Process incoming chat dump using Gemma 4 AI Agent."""
    data = request.get_json(force=True, silent=True) or {}
    chat_dump = data.get("chat_dump", "")
    model = data.get("model", DEFAULT_MODEL)

    if not chat_dump.strip():
        return jsonify({"success": False, "error": "Please provide or paste a hostel chat dump."}), 400

    result = triage_hostel_chat(chat_dump=chat_dump, model=model)
    return jsonify(result)


@app.route("/api/format_whatsapp", methods=["POST"])
def format_whatsapp():
    """Generate clean, emoji-formatted WhatsApp digest for warden / maintenance staff."""
    data = request.get_json(force=True, silent=True) or {}
    complaints = data.get("complaints", [])

    if not complaints:
        return jsonify({"formatted_text": "No complaints to format."})

    lines = [
        "🚨 *HOSTEL INCIDENT TRIAGE DIGEST* 🚨",
        "Generated via Gemma AI Agent for Warden Quick Skim\n"
    ]

    critical = [c for c in complaints if c.get("urgency") == "Critical"]
    high = [c for c in complaints if c.get("urgency") == "High"]
    medium = [c for c in complaints if c.get("urgency") == "Medium"]
    low = [c for c in complaints if c.get("urgency") == "Low"]

    if critical:
        lines.append("🔴 *CRITICAL (IMMEDIATE HAZARD / LIFE-SAFETY)*")
        for c in critical:
            lines.append(f"• *[{c.get('room')}]* {c.get('one_line_summary')}")
            lines.append(f"  ⚡ Action: {c.get('action_required')}\n")

    if high:
        lines.append("🟠 *HIGH PRIORITY (DISPATCH REQUIRED)*")
        for c in high:
            lines.append(f"• *[{c.get('room')}]* {c.get('one_line_summary')}")
            lines.append(f"  ⚡ Action: {c.get('action_required')}\n")

    if medium:
        lines.append("🟡 *MEDIUM PRIORITY (MAINTENANCE LOG)*")
        for c in medium:
            lines.append(f"• *[{c.get('room')}]* {c.get('one_line_summary')}")

    if low:
        lines.append("\n🟢 *ROUTINE / LOW PRIORITY*")
        for c in low:
            lines.append(f"• *[{c.get('room')}]* {c.get('one_line_summary')}")

    missing_rooms = [c for c in complaints if c.get("has_missing_room")]
    if missing_rooms:
        lines.append("\n⚠️ *ACTION REQUIRED: MISSING ROOM NUMBERS*")
        for c in missing_rooms:
            lines.append(f'• Need room for: "{c.get("student_raw")[:60]}..."')

    formatted = "\n".join(lines)
    return jsonify({"formatted_text": formatted})


@app.route("/api/dispatch_audio", methods=["POST"])
def dispatch_audio():
    """Synthesize high-fidelity native audio dispatch for Walkie-Talkie on macOS."""
    data = request.get_json() or {}
    text = data.get("text", "")
    voice = data.get("voice", "Samantha")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # On macOS, use native high-fidelity audio synthesis to produce a genuine .wav audio file
    if sys.platform == "darwin":
        try:
            safe_text = text.replace('"', '').replace('$', '').replace('`', '').strip()
            if len(safe_text) > 320:
                safe_text = safe_text[:320] + "... Over and out."

            out_wav = os.path.join(tempfile.gettempdir(), f"walkie_dispatch_{os.getpid()}_{uuid.uuid4().hex[:6]}.wav")
            cmd = ["say", "-v", voice, "-o", out_wav, "--data-format=LEI16@22050", safe_text]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0 and os.path.exists(out_wav) and os.path.getsize(out_wav) > 1000:
                return send_file(out_wav, mimetype="audio/wav")

            # Fallback to default say voice if chosen voice is not installed
            cmd_default = ["say", "-o", out_wav, "--data-format=LEI16@22050", safe_text]
            res2 = subprocess.run(cmd_default, capture_output=True, text=True, timeout=8)
            if res2.returncode == 0 and os.path.exists(out_wav) and os.path.getsize(out_wav) > 1000:
                return send_file(out_wav, mimetype="audio/wav")
        except Exception as e:
            logger.warning(f"Native audio synthesis error: {e}")

    return jsonify({"fallback_to_browser": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"🏨 Hostel Complaint Triage Agent starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
