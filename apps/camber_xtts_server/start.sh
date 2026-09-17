#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Downloading Cloudflare Tunnel (cloudflared)..."
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
chmod +x cloudflared

echo "Starting FastAPI XTTSv2 Server in the background..."
python main.py &

echo "Waiting for server to start..."
sleep 15

echo "Starting Cloudflare Tunnel..."
echo "================================================================"
echo "LOOK FOR THE URL BELOW (it looks like https://xxxx.trycloudflare.com)"
echo "Send this URL to the frontend/app team!"
echo "================================================================"
./cloudflared tunnel --url http://127.0.0.1:8000
