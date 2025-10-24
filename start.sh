#!/bin/bash
# SPEAR Climate Chatbot - Start Script (Podman)

echo "🚀 Starting SPEAR Climate Chatbot with Podman..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo "Creating .env from template..."
    cp .env.template .env
    echo ""
    echo "📝 Please edit .env and add your configuration:"
    echo "   ANTHROPIC_API_KEY=sk-ant-api03-..."
    echo "   MCP_SERVER_URL=http://localhost:8000"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if API key is set
if grep -q "your_api_key_here" .env; then
    echo "⚠️  API key not configured in .env file!"
    echo "📝 Please edit .env and add your Anthropic API key:"
    echo "   ANTHROPIC_API_KEY=sk-ant-api03-..."
    exit 1
fi

# Source the .env file to get variables
source .env

# Check if MCP server is running
echo "🔍 Checking MCP server connection..."
if ! curl -s -f "${MCP_SERVER_URL}/health" > /dev/null 2>&1; then
    echo "⚠️  WARNING: Cannot reach MCP server at ${MCP_SERVER_URL}"
    echo "Make sure the SPEAR MCP server is running first!"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build the container image
echo "🔨 Building Podman image..."
podman build -t spear-chatbot .

# Stop and remove existing container if it exists
if podman ps -a --format "{{.Names}}" | grep -q "^spear-chatbot$"; then
    echo "🛑 Stopping existing container..."
    podman stop spear-chatbot
    podman rm spear-chatbot
fi

# Run the container
echo "▶️  Starting container..."
podman run -d \
    --name spear-chatbot \
    -p 8501:8501 \
    --env-file .env \
    --restart unless-stopped \
    spear-chatbot

# Wait a moment for container to start
sleep 3

# Check if container is running
if podman ps --format "{{.Names}}" | grep -q "^spear-chatbot$"; then
    echo ""
    echo "✅ SPEAR Climate Chatbot is running!"
    echo "🌐 Open your browser to: http://localhost:8501"
    echo ""
    echo "📋 Useful commands:"
    echo "   ./logs.sh    - View logs"
    echo "   ./stop.sh    - Stop the chatbot"
    echo "   ./rebuild.sh - Rebuild after code changes"
else
    echo ""
    echo "❌ Failed to start container. Check logs with:"
    echo "   podman logs spear-chatbot"
    exit 1
fi
