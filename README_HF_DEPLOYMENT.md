# PhaseGuard Hugging Face Spaces Deployment Guide

## Prerequisites
- Hugging Face account (free)
- Git installed
- PhaseGuard codebase

## Step 1: Create Hugging Face Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Choose:
   - **Space Name:** phaseguard-api
   - **License:** MIT
   - **SDK:** Docker
   - **Hardware:** T4 GPU (Free) or A10G GPU (Paid)

## Step 2: Prepare Code for Deployment

```bash
# Clone your space
git clone https://huggingface.co/spaces/YOUR_USERNAME/phaseguard-api
cd phaseguard-api

# Copy backend code
cp -r /path/to/PhaseGuard/apps/api/* .

# Create requirements.txt (Hugging Face version)
cat > requirements.txt << 'EOF'
fastapi==0.115.5
uvicorn[standard]==0.32.1
websockets==13.1
pydantic==2
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
slowapi==0.1.9
numpy==1.26.4
scipy==1.13.1
soundfile==0.12.1
librosa==0.10.1
reportlab==4.2.0
matplotlib==3.9.0
opencv-python==4.10.0.84
gtts==2.5.1
TTS==0.22.0
groq==0.11.0
httpx==0.27.0
duckduckgo-search==5.3.0
pydub==0.25.1
EOF

# Create Dockerfile for Hugging Face
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    sox \
    libsox-dev \
    libsox-fmt-all \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
EOF

# Create .env file for Hugging Face
cat > .env << 'EOF'
# Hugging Face Environment Variables
WS_HOST=0.0.0.0
WS_PORT=7860
DEBUG=false
ENVIRONMENT=production

# Auth
JWT_SECRET=CHANGE_ME_TO_RANDOM_VALUE_IN_HF_DEPLOYMENT
JWT_TTL_MINUTES=15

# Groq API
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_STT_MODEL=whisper-large-v3
GROQ_LLM_MODEL=openai/gpt-oss-120b

# Search APIs
SERPER_API_KEY=YOUR_SERPER_API_KEY
TAVILY_API_KEY=YOUR_TAVILY_API_KEY

# TTS Configuration (XTTS with fallback)
TTS_BACKEND=xtts
TTS_LANGUAGE=hi

# Other configuration
SAMPLE_RATE=16000
DSP_VOICE_DETECTION_ENABLED=true
INGESTION_MODE=browser_mic
SECRET_MANAGER_BACKEND=env
EOF

# Commit and push
git add .
git commit -m "Deploy PhaseGuard with XTTS voice cloning"
git push
```

## Step 3: Configure Environment Variables in Hugging Face

1. Go to your Space settings
2. Click "Settings" → "Variables"
3. Add the following variables:
   - `GROQ_API_KEY`: Your Groq API key
   - `SERPER_API_KEY`: Your Serper API key
   - `TAVILY_API_KEY`: Your Tavily API key
   - `JWT_SECRET`: Random secret string
   - `TTS_BACKEND`: xtts
   - `TTS_LANGUAGE`: hi

## Step 4: Monitor Deployment

1. Go to your Space: https://huggingface.co/spaces/YOUR_USERNAME/phaseguard-api
2. Watch the build logs
3. Wait for XTTS model to download (first time ~2GB)
4. Check that the API is running

## Step 5: Update Flutter App

```dart
// In Flutter app, update API base URL
final String apiBaseUrl = 'https://YOUR_USERNAME-phaseguard-api.hf.space';
```

## Cost Estimation

- **Free T4 GPU:** $0/hour (limited hours per month)
- **Paid A10G GPU:** ~$0.10/hour
- **Hackathon duration (10 hours):** ~$1 (A10G)

## Testing XTTS on Hugging Face

```bash
# Test the deployed API
curl https://YOUR_USERNAME-phaseguard-api.hf.space/health

# Test voice cloning
curl -X POST https://YOUR_USERNAME-phaseguard-api.hf.space/call/init \
  -H "Content-Type: application/json" \
  -d '{"ingestion_mode": "browser_mic"}'
```

## Troubleshooting

**XTTS Model Not Loading:**
- Check if GPU is assigned
- Wait for model download (first deployment)
- Check logs for memory issues

**Fallback to gTTS:**
- If XTTS fails, it automatically falls back to gTTS
- This ensures the system always works
- Check logs for fallback messages

**Performance Issues:**
- XTTS takes 3-5 seconds on CPU
- GPU reduces to 1-2 seconds
- Consider using T4 GPU for better performance

## Success Indicators

✅ Space status: "Running"
✅ Health endpoint returns OK
✅ XTTS model loaded in logs
✅ Fallback system working
✅ API responding to requests