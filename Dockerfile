FROM python:3.11-slim

WORKDIR /app

# Install git (needed for GitPython)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data memory/knowledge agent/data agent/improvements

# Set git config for auto-commits
RUN git config --global user.email "the-constituent@agents-republic.org" && \
    git config --global user.name "The Constituent"

# Default command: run the agent with Telegram bot
CMD ["python", "-m", "agent.main_v2"]
