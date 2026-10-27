# 🚀 Deployment Guide: Hostel Complaint Triage AI

This guide covers 3 deployment methods tailored for hackathon demos, presentation tables, and production servers.

---

## ⚡ Method 1: Instant Public Link for Hackathon Judges (Recommended)
> **Best for:** Showing live on judges' smartphones, tablets, or remote evaluation without paying for cloud GPUs.

Since you already have `gemma4:latest` running locally, you can expose your local port `5001` to a secure public HTTPS link in 10 seconds using **localtunnel** (zero installation needed, runs directly with your installed `npx`):

```bash
# In your terminal, run:
npx localtunnel --port 5001
```

It will output:
```
your url is: https://hostel-triage-xyz.loca.lt
```
👉 Share that link with judges or open it on your phone! It routes requests directly to your local Gemma 4 model.

---

## 🐳 Method 2: Docker Container (Any Cloud VM / VPS)
> **Best for:** Deploying on AWS EC2, GCP Compute Engine, DigitalOcean Droplet, or RunPod.

A complete `Dockerfile` and `docker-compose.yml` are included in the project directory.

### Quick Commands:
```bash
cd /Users/vivekdalmia/.gemini/antigravity/scratch/hostel-complaint-triage

# Build and start both Ollama and the Flask Web App
docker compose up -d --build

# Pull Gemma 4 inside the Docker Ollama container
docker exec -it hostel_ollama ollama pull gemma4:latest
```

The app will be accessible at `http://<your-server-ip>:5001`.

---

## ☁️ Method 3: 1-Click Cloud Deploy (Render / Railway)
> **Best for:** Permanent web hosting with a custom domain.

1. **Push your repository to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Hostel Complaint Triage AI"
   git branch -M main
   git remote add origin https://github.com/<your-username>/hostel-complaint-triage.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com) and click **New +** &rarr; **Web Service**.
   - Select your GitHub repo.
   - **Environment:** Python 3 (or Docker)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
   - **Environment Variable:**
     - `OLLAMA_HOST`: `<URL to your cloud Ollama or GPU instance>`

---

## ⚙️ Configuration Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5001` | HTTP port for the web dashboard |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Endpoint for Ollama API |
| `GEMMA_MODEL` | `gemma4:latest` | Target model name |
