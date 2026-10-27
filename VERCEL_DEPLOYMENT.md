# ⚡ Vercel Deployment Guide: Hostel Complaint Triage AI

## ❓ Can you deploy this on Vercel?
**YES!** Vercel can host your Flask web application and dashboard for **100% free**.

> ⚠️ **Important Architecture Note:**  
> Vercel is a **serverless cloud** with a strict 250MB limit per function and no GPU hardware. A 9.5GB Gemma model cannot run *inside* Vercel's serverless sandbox.  
> However, Vercel connects effortlessly to:
> 1. **Option A (Zero Setup):** Your local Gemma 4 via your active tunnel URL (`OLLAMA_HOST`).
> 2. **Option B (100% Autonomous Cloud):** Groq's free cloud open-source Gemma endpoint (`gemma2-9b-it`) using a free `GROQ_API_KEY`.

---

## 🚀 How to Deploy to Vercel (3 Steps)

### Step 1: Push your code to GitHub
```bash
cd /Users/vivekdalmia/.gemini/antigravity/scratch/hostel-complaint-triage

git init
git add .
git commit -m "Hostel Complaint Triage AI Ready for Vercel"
git branch -M main
git remote add origin https://github.com/<your-username>/hostel-complaint-triage.git
git push -u origin main
```

---

### Step 2: Import into Vercel
1. Go to [vercel.com](https://vercel.com) and log in with GitHub.
2. Click **"Add New..."** &rarr; **"Project"**.
3. Select your `hostel-complaint-triage` repository.
4. **Framework Preset:** Leave as `Other` (Vercel automatically detects `vercel.json` and Python).

---

### Step 3: Add Your Environment Variables in Vercel
Before clicking "Deploy", open the **Environment Variables** section:

#### Choose One:
* **Option A: Connect to your running Mac Gemma 4**
  - Key: `OLLAMA_HOST`
  - Value: `https://parrots-hammer.loca.lt` (or your active tunnel URL)

* **Option B: Run 100% on Cloud with Free Gemma (No laptop needed!)**
  - Key: `GROQ_API_KEY`
  - Value: `<your-free-groq-key>` (Get one free in 30 seconds at [console.groq.com/keys](https://console.groq.com/keys))
  - Key: `GROQ_MODEL`
  - Value: `gemma2-9b-it`

Click **Deploy**! In ~60 seconds, you get a live `https://hostel-complaint-triage.vercel.app` URL.

---

## 📁 Pre-Configured Vercel Files in this Project:
- [`vercel.json`](file:///Users/vivekdalmia/.gemini/antigravity/scratch/hostel-complaint-triage/vercel.json): Directs Vercel's Python Serverless builder to `app.py`.
- [`requirements.txt`](file:///Users/vivekdalmia/.gemini/antigravity/scratch/hostel-complaint-triage/requirements.txt): Contains `Flask`, `requests`, and `gunicorn`.
- [`triage_agent.py`](file:///Users/vivekdalmia/.gemini/antigravity/scratch/hostel-complaint-triage/triage_agent.py): Auto-detects whether to run via Cloud Gemma (`GROQ_API_KEY`), Remote Ollama (`OLLAMA_HOST`), or Local Ollama.
