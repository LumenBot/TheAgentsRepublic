# Deployment Guide — The Constituent

## Quick Start

```bash
# Clone and setup
git clone https://github.com/LumenBot/TheAgentsRepublic.git /opt/TheAgentsRepublic
cd /opt/TheAgentsRepublic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials
```

## Option A: systemd (recommended for Linux VPS)

```bash
# Install service
sudo cp deploy/systemd/the-constituent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable the-constituent
sudo systemctl start the-constituent

# Check status
sudo systemctl status the-constituent
sudo journalctl -u the-constituent -f  # Live logs
```

## Option B: Supervisor (any Linux)

```bash
sudo apt install supervisor
sudo mkdir -p /var/log/the-constituent
sudo cp deploy/supervisor/the-constituent.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start the-constituent

# Check status
sudo supervisorctl status the-constituent
tail -f /var/log/the-constituent/output.log
```

## Option C: Docker

```bash
docker build -t the-constituent -f deploy/Dockerfile .
docker run -d --name constituent --env-file .env --restart always the-constituent
```

## Option D: PM2 (Node.js process manager)

```bash
npm install -g pm2
pm2 start "python -m agent" --name the-constituent --cwd /opt/TheAgentsRepublic
pm2 save
pm2 startup  # Auto-start on reboot
```

## Health Check

Once running, the agent exposes a health endpoint:

```bash
curl http://localhost:8080/health
# {"status": "ok", "uptime": 3600, "heartbeat_ticks": 6, ...}
```

## Environment Variables

See `.env.example` for all required variables. Critical ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | YES | Claude API key |
| `TELEGRAM_BOT_TOKEN` | YES | Telegram bot token |
| `OPERATOR_TELEGRAM_CHAT_ID` | YES | Your Telegram chat ID |
| `BASE_RPC_URL` | YES | Base L2 RPC (e.g. Alchemy) |
| `AGENT_WALLET_ADDRESS` | YES | Agent wallet on Base |
| `AGENT_WALLET_PRIVATE_KEY` | YES | Wallet private key |
