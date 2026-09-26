#!/bin/bash
# deploy.sh — Deploy the Python sidecar + Ollama LLM to the Raspberry Pi.
#
# Prerequisites:
#   - SSH access to pi@<ip> (key-based, no passphrase)
#   - The C++ backend must be reconfigured to listen on port 8080
#   - sudo access is needed for nginx, systemd, and Ollama install (manual steps)
#
# Usage:
#   ./deploy.sh <pi-ip>
#   ./deploy.sh 192.168.4.1
#
# What this script does (non-destructive):
#   1. Copies sidecar files to ~/lunyoro-sidecar/ on the Pi
#   2. Creates a Python venv and installs dependencies
#   3. Downloads MobileNetV2 model (requires internet on first run)
#   4. Prints manual steps for Ollama install, nginx, and systemd (needs sudo)

set -e

PI_IP="${1:-192.168.4.1}"
PI="pi@${PI_IP}"
REMOTE_DIR="/home/pi/lunyoro-sidecar"

echo "=== Deploying Pi Sidecar + Ollama config to ${PI} ==="

# 1. Copy sidecar files (including new service files)
echo "[1/4] Copying sidecar files..."
ssh "$PI" "mkdir -p ${REMOTE_DIR}"
scp app.py language_rules_data.py requirements.txt download_model.py \
    lunyoro-sidecar.service ollama-pull.service nginx-translator.conf \
    "$PI:${REMOTE_DIR}/"

# 2. Create venv and install deps
echo "[2/4] Setting up Python virtual environment..."
ssh "$PI" "
    cd ${REMOTE_DIR}
    python3 -m venv venv 2>/dev/null || python -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
"

# 3. Download MobileNetV2 (needs internet — skip if already cached)
echo "[3/4] Downloading MobileNetV2 model..."
ssh "$PI" "
    cd ${REMOTE_DIR}
    if [ -d models/mobilenet_v2 ] && ls models/mobilenet_v2/*.json >/dev/null 2>&1; then
        echo '  [OK] MobileNetV2 already cached'
    else
        ./venv/bin/python download_model.py
    fi
"

# 4. Print manual steps
echo ""
echo "[4/4] === MANUAL STEPS (need sudo) ==="
echo ""
echo "SSH into the Pi and run the following in order:"
echo ""
echo "  ── Step 1: Install Ollama (skip if already installed) ──────────────"
echo "  curl -fsSL https://ollama.com/install.sh | sh"
echo "  # This installs Ollama as a systemd service that starts at boot."
echo "  # Verify: systemctl is-active ollama"
echo ""
echo "  ── Step 2: Install the model-pull service ───────────────────────────"
echo "  sudo cp ${REMOTE_DIR}/ollama-pull.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable ollama-pull"
echo "  # Pull the model now (first time only, ~986 MB):"
echo "  sudo systemctl start ollama-pull"
echo "  # Wait for it to finish:"
echo "  journalctl -u ollama-pull -f"
echo ""
echo "  ── Step 3: Install / update the sidecar service ─────────────────────"
echo "  sudo cp ${REMOTE_DIR}/lunyoro-sidecar.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable lunyoro-sidecar"
echo ""
echo "  ── Step 4: Configure the C++ backend port ───────────────────────────"
echo "  #    Edit the C++ service override to add --port 8080 to ExecStart:"
echo "  sudo nano /etc/systemd/system/lunyoro-translator.service.d/override.conf"
echo ""
echo "  ── Step 5: Install nginx (if not already) ───────────────────────────"
echo "  sudo apt-get install -y nginx"
echo "  sudo cp ${REMOTE_DIR}/nginx-translator.conf /etc/nginx/sites-available/lunyoro-translator"
echo "  sudo ln -sf /etc/nginx/sites-available/lunyoro-translator /etc/nginx/sites-enabled/"
echo "  sudo rm -f /etc/nginx/sites-enabled/default"
echo "  sudo nginx -t && sudo systemctl restart nginx"
echo ""
echo "  ── Step 6: Restart everything ───────────────────────────────────────"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart lunyoro-translator"
echo "  sudo systemctl restart lunyoro-sidecar"
echo "  sudo systemctl restart nginx"
echo ""
echo "  ── Step 7: Verify ───────────────────────────────────────────────────"
echo "  systemctl is-active ollama lunyoro-translator lunyoro-sidecar nginx"
echo "  # All four should print 'active'"
echo "  curl -s http://localhost/health | python3 -m json.tool"
echo "  curl -s -X POST http://localhost/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"How are you?\"}' | python3 -m json.tool"
echo "  # Expected: reply in Runyoro with English alongside"
echo ""
echo "=== Deployment files copied. Complete manual steps above. ==="
