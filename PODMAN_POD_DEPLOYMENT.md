# SPEAR Chatbot - Podman Pod Deployment Guide

Complete guide for deploying the SPEAR Climate Chatbot and MCP Server together in a Podman pod.

## Architecture

```
┌─────────────────────────────────────────┐
│           Podman Pod: spear-pod         │
├─────────────────────────────────────────┤
│                                         │
│  Container 1: spear-mcp-server          │
│  - Port: 8000 (internal)                │
│  - Provides SPEAR data access via MCP   │
│  - Direct S3 connection to SPEAR data   │
│                                         │
│  Container 2: spear-chatbot             │
│  - Port: 8501 (exposed)                 │
│  - Streamlit web interface              │
│  - Claude AI integration                │
│  - Connects to MCP server via localhost │
│                                         │
└─────────────────────────────────────────┘
         │
         └──> Port 8501 mapped to host
```

## Prerequisites

- **Podman** installed (rootless mode recommended)
- **Anthropic API key** from https://console.anthropic.com/
- **SPEAR MCP server** container image built

## Quick Start

### 1. Build the Chatbot Image

```bash
cd spear-chatbot-app/
podman build -t spear-chatbot .
```

### 2. Configure Environment

```bash
cp .env.template .env
nano .env
```

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
MCP_SERVER_URL=http://localhost:8000
```

### 3. Create and Start the Pod

```bash
# Create pod with port mapping
podman pod create --name spear-pod -p 8501:8501

# Start MCP server (replace with your MCP image name)
podman run -d \
    --pod spear-pod \
    --name spear-mcp-server \
    localhost/spear-mcp-server:latest

# Wait for MCP server to be ready
sleep 5

# Start chatbot
podman run -d \
    --pod spear-pod \
    --name spear-chatbot \
    --env-file .env \
    --restart unless-stopped \
    spear-chatbot
```

### 4. Access the Chatbot

Open your browser to: **http://localhost:8501**

## Pod Management Commands

### Check Pod Status

```bash
# List all pods
podman pod ps

# List containers in the pod
podman ps --pod
```

### View Logs

```bash
# Chatbot logs
podman logs -f spear-chatbot

# MCP server logs
podman logs -f spear-mcp-server
```

### Stop the Pod

```bash
# Stop all containers in the pod
podman pod stop spear-pod

# Remove the pod (stops and removes all containers)
podman pod rm -f spear-pod
```

### Restart the Pod

```bash
# Restart all containers
podman pod restart spear-pod

# Or restart individual containers
podman restart spear-chatbot
podman restart spear-mcp-server
```

## Automated Pod Deployment Script

Create `deploy-pod.sh`:

```bash
#!/bin/bash
# SPEAR Pod Deployment Script

set -e

echo "🚀 Deploying SPEAR Chatbot Pod..."

# Configuration
POD_NAME="spear-pod"
CHATBOT_IMAGE="spear-chatbot"
MCP_IMAGE="localhost/spear-mcp-server:latest"  # Update with your MCP image

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Run: cp .env.template .env and configure it"
    exit 1
fi

# Remove existing pod if it exists
if podman pod exists ${POD_NAME}; then
    echo "🛑 Removing existing pod..."
    podman pod rm -f ${POD_NAME}
fi

# Create pod
echo "📦 Creating pod: ${POD_NAME}"
podman pod create --name ${POD_NAME} -p 8501:8501

# Start MCP server
echo "▶️  Starting MCP server..."
podman run -d \
    --pod ${POD_NAME} \
    --name spear-mcp-server \
    --restart unless-stopped \
    ${MCP_IMAGE}

# Wait for MCP server to be ready
echo "⏳ Waiting for MCP server to start..."
sleep 5

# Verify MCP server is running
if ! podman exec spear-mcp-server curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: MCP server health check failed"
fi

# Start chatbot
echo "▶️  Starting chatbot..."
podman run -d \
    --pod ${POD_NAME} \
    --name spear-chatbot \
    --env-file .env \
    --restart unless-stopped \
    ${CHATBOT_IMAGE}

# Wait for chatbot to start
sleep 3

# Check pod status
echo ""
echo "📊 Pod Status:"
podman pod ps --filter name=${POD_NAME}

echo ""
echo "✅ Deployment complete!"
echo "🌐 Access the chatbot at: http://localhost:8501"
echo ""
echo "📋 Useful commands:"
echo "   podman pod ps                    - View pod status"
echo "   podman logs -f spear-chatbot     - View chatbot logs"
echo "   podman logs -f spear-mcp-server  - View MCP server logs"
echo "   podman pod stop ${POD_NAME}      - Stop the pod"
echo "   podman pod rm -f ${POD_NAME}     - Remove the pod"
```

Make it executable:
```bash
chmod +x deploy-pod.sh
./deploy-pod.sh
```

## Systemd Integration (Optional)

For automatic startup on boot, create a systemd user service:

### 1. Generate Systemd Unit Files

```bash
# Generate pod unit file
podman generate systemd --new --name spear-pod \
    --files \
    --restart-policy=always

# Move to systemd user directory
mkdir -p ~/.config/systemd/user/
mv pod-spear-pod.service ~/.config/systemd/user/
```

### 2. Enable and Start Service

```bash
# Reload systemd
systemctl --user daemon-reload

# Enable service to start on boot
systemctl --user enable pod-spear-pod.service

# Start the service
systemctl --user start pod-spear-pod.service

# Check status
systemctl --user status pod-spear-pod.service
```

### 3. Enable Linger (For Rootless Podman)

```bash
# Allow user services to run after logout
loginctl enable-linger $USER
```

## Networking Details

### Pod Network Model

In a Podman pod:
- All containers share the same network namespace
- Containers can communicate via `localhost`
- Only the pod's ports are exposed to the host

### Container Communication

The chatbot connects to the MCP server using:
```bash
MCP_SERVER_URL=http://localhost:8000
```

This works because both containers are in the same pod.

## Volume Mounts (Optional)

### Persist Chat Logs

```bash
# Create volume
podman volume create spear-chat-logs

# Run chatbot with volume
podman run -d \
    --pod spear-pod \
    --name spear-chatbot \
    --env-file .env \
    -v spear-chat-logs:/app/chat_logs \
    spear-chatbot
```

### Add Custom Reference Documents

```bash
podman run -d \
    --pod spear-pod \
    --name spear-chatbot \
    --env-file .env \
    -v ./my-documents:/app/reference_documents:ro \
    spear-chatbot
```

## Troubleshooting

### Chatbot Can't Connect to MCP Server

**Check MCP server is running:**
```bash
podman ps --filter name=spear-mcp-server
```

**Test MCP server health:**
```bash
podman exec spear-mcp-server curl http://localhost:8000/health
```

**Check MCP server logs:**
```bash
podman logs spear-mcp-server
```

### Port Already in Use

**Find process using port 8501:**
```bash
lsof -i :8501
```

**Use different port:**
```bash
# Recreate pod with different port
podman pod create --name spear-pod -p 8502:8501
```

### Container Crashes on Startup

**View logs:**
```bash
podman logs spear-chatbot
```

**Check environment variables:**
```bash
podman exec spear-chatbot env | grep -E "ANTHROPIC|MCP"
```

### Permission Denied Errors (Rootless)

**Ensure proper permissions:**
```bash
# Check subuid/subgid
grep $USER /etc/subuid
grep $USER /etc/subgid

# If missing, add them:
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER
```

## Resource Limits

Set resource limits for production:

```bash
podman run -d \
    --pod spear-pod \
    --name spear-chatbot \
    --env-file .env \
    --memory="2g" \
    --cpus="1.0" \
    spear-chatbot
```

## Security Considerations

### Run as Non-Root (Rootless Podman)

Podman supports rootless containers by default - use your regular user account.

### Restrict Network Access

```bash
# Create pod with custom network
podman network create spear-network

podman pod create --name spear-pod \
    --network spear-network \
    -p 8501:8501
```

### SELinux Contexts (RHEL/Fedora)

```bash
# If using volumes with SELinux
podman run -d \
    --pod spear-pod \
    --name spear-chatbot \
    --env-file .env \
    -v ./chat_logs:/app/chat_logs:z \
    spear-chatbot
```

## Backup and Migration

### Export Pod Configuration

```bash
# Save pod as archive
podman pod save spear-pod -o spear-pod.tar

# On another system
podman pod load -i spear-pod.tar
```

### Export Chatbot Image

```bash
podman save -o spear-chatbot.tar localhost/spear-chatbot:latest

# Transfer to another system and load
podman load -i spear-chatbot.tar
```

## Monitoring

### Check Resource Usage

```bash
podman pod stats spear-pod
```

### Health Checks

```bash
# Chatbot health
curl http://localhost:8501/_stcore/health

# MCP server health
podman exec spear-mcp-server curl http://localhost:8000/health
```

## Complete Example: Production Deployment

```bash
#!/bin/bash
# Production deployment with all features

set -e

POD_NAME="spear-pod"
CHATBOT_IMAGE="spear-chatbot:latest"
MCP_IMAGE="spear-mcp-server:latest"

# Create pod with resource limits
podman pod create --name ${POD_NAME} \
    -p 8501:8501 \
    --memory="4g" \
    --cpus="2.0"

# Create volumes
podman volume create spear-chat-logs

# Start MCP server
podman run -d \
    --pod ${POD_NAME} \
    --name spear-mcp-server \
    --restart unless-stopped \
    --memory="2g" \
    --cpus="1.0" \
    ${MCP_IMAGE}

# Wait for MCP ready
sleep 10

# Start chatbot with volume
podman run -d \
    --pod ${POD_NAME} \
    --name spear-chatbot \
    --env-file .env \
    --restart unless-stopped \
    --memory="2g" \
    --cpus="1.0" \
    -v spear-chat-logs:/app/chat_logs \
    ${CHATBOT_IMAGE}

# Generate systemd service
podman generate systemd --new --name ${POD_NAME} \
    --files --restart-policy=always

mv pod-${POD_NAME}.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable pod-${POD_NAME}.service

echo "✅ Production deployment complete!"
echo "🌐 Access at: http://localhost:8501"
```

## Support

For issues:
- Check pod status: `podman pod ps`
- View logs: `podman logs -f spear-chatbot`
- Inspect pod: `podman pod inspect spear-pod`
- Review this guide and DEPLOYMENT.md

## Acknowledgments

- NOAA-GFDL for SPEAR climate model data
- Anthropic for Claude AI
- Podman for containerization
