#!/bin/bash
# SPEAR Climate Chatbot - Stop Script (Podman)

echo "🛑 Stopping SPEAR Climate Chatbot..."

# Stop and remove the container
podman stop spear-chatbot 2>/dev/null
podman rm spear-chatbot 2>/dev/null

echo "✅ Chatbot stopped!"
