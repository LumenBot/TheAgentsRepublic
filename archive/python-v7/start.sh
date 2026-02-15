#!/bin/bash
# ============================================
# The Constituent — Quick Start Script
# ============================================
# Use this if Docker is not available.
# Works with regular Python 3.11+ installation.
# ============================================

set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     THE CONSTITUENT — Setup & Start          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Install Python 3.11+ first."
        exit 1
    fi
    PYTHON=python
else
    PYTHON=python3
fi

echo "✅ Python found: $($PYTHON --version)"

# Check .env
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "   Copy .env.example to .env and fill in your API keys:"
    echo "   cp .env.example .env"
    echo ""
    exit 1
fi
echo "✅ .env file found"

# Create virtual environment if not exists
if [ ! -d .venv ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    $PYTHON -m venv .venv
fi

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
fi
echo "✅ Virtual environment active"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Create directories
mkdir -p data memory/knowledge agent/data agent/improvements

# Start the agent
echo ""
echo "🚀 Starting The Constituent..."
echo ""
$PYTHON -m agent.main_v2
