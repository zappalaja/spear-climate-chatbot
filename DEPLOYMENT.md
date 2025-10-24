# SPEAR Climate Chatbot - Deployment Guide

Complete guide for deploying the SPEAR Climate Chatbot using Docker.

## Prerequisites

### Required Software

- **Docker** 20.10 or later
- **Docker Compose** 2.0 or later
- **Anthropic API Key** (get from https://console.anthropic.com/)

### System Requirements

- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: 2GB minimum (4GB recommended)
- **Disk**: 1GB for Docker image + data cache
- **Network**: Internet connection for AWS S3 access

## Quick Start

### 1. Clone or Copy the Application

```bash
# If using Git
git clone https://github.com/YOUR_USERNAME/spear-chatbot.git
cd spear-chatbot

# Or simply copy the spear-chatbot-app/ folder to your deployment machine
```

### 2. Configure API Key

```bash
# Create .env file from template
cp .env.template .env

# Edit .env and add your API key
nano .env  # or use your preferred editor
```

Your `.env` file should look like:
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
```

### 3. Start the Chatbot

```bash
./start.sh
```

The script will:
- Check if `.env` exists and is configured
- Build the Docker image
- Start the container in detached mode
- Display the access URL

### 4. Access the Application

Open your browser to: **http://localhost:8501**

## Management Scripts

### Start the Chatbot

```bash
./start.sh
```

Builds and starts the chatbot. Checks for API key configuration first.

### Stop the Chatbot

```bash
./stop.sh
```

Stops the running container gracefully.

### View Logs

```bash
./logs.sh
```

Shows real-time logs. Press Ctrl+C to exit.

### Rebuild After Changes

```bash
./rebuild.sh
```

Stops the container, rebuilds the Docker image with `--no-cache`, and restarts.

## Docker Commands (Alternative)

If you prefer using Docker Compose directly:

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

## Verification

### Check Container Status

```bash
docker ps | grep spear-chatbot
```

Should show a running container on port 8501.

### Check Health

```bash
docker exec spear-chatbot curl -f http://localhost:8501/_stcore/health
```

Should return HTTP 200 if healthy.

### Test API Connection

Navigate to http://localhost:8501 and ask:
```
What variables are available in SPEAR?
```

The chatbot should browse the SPEAR directory and list available variables.

## Troubleshooting

### "Cannot connect to Docker daemon"

**Problem**: Docker is not running.

**Solution**:
```bash
# Linux
sudo systemctl start docker

# macOS/Windows
# Start Docker Desktop
```

### "Port 8501 already in use"

**Problem**: Another service is using port 8501.

**Solution**:
```bash
# Find process using port
lsof -i :8501

# Kill process or change port in docker-compose.yml
ports:
  - "8502:8501"  # Use 8502 instead
```

### "Invalid API key"

**Problem**: API key not set or incorrect.

**Solution**:
```bash
# Verify .env file exists and has correct key
cat .env

# Restart container after fixing
./rebuild.sh
```

### "ModuleNotFoundError" in logs

**Problem**: Missing Python dependencies.

**Solution**:
```bash
# Rebuild with --no-cache to ensure fresh install
./rebuild.sh
```

### Container crashes or restarts repeatedly

**Problem**: Application error.

**Solution**:
```bash
# View logs to see error
./logs.sh

# Common issues:
# 1. Missing API key → Edit .env
# 2. Invalid Python syntax → Check recent code changes
# 3. Missing files → Ensure all files copied correctly
```

## Deployment to Remote Server

### 1. Transfer Files

```bash
# Using rsync
rsync -avz spear-chatbot-app/ user@server:/path/to/deployment/

# Or use scp
scp -r spear-chatbot-app/ user@server:/path/to/deployment/
```

### 2. SSH to Server and Deploy

```bash
ssh user@server
cd /path/to/deployment/spear-chatbot-app/

# Configure API key
cp .env.template .env
nano .env

# Start chatbot
./start.sh
```

### 3. Access Remotely

If deploying to a server, you'll need to:

**Option A: Port Forwarding**
```bash
ssh -L 8501:localhost:8501 user@server
# Then access http://localhost:8501 on your local machine
```

**Option B: Reverse Proxy (Production)**

Use Nginx or Traefik to expose the chatbot with HTTPS:

```nginx
# Nginx example
server {
    listen 80;
    server_name chatbot.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Security Considerations

### API Key Protection

- **NEVER commit .env** to version control (already in .gitignore)
- Use environment variables for production deployments
- Rotate API keys regularly

### Network Security

- Use HTTPS in production (reverse proxy with Let's Encrypt)
- Restrict access with firewall rules
- Consider authentication layer for multi-user deployments

### Docker Security

```bash
# Run container with resource limits
docker run -d \
  --memory="2g" \
  --cpus="1.0" \
  -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your_key \
  spear-chatbot
```

## Monitoring

### Check Resource Usage

```bash
docker stats spear-chatbot
```

Shows CPU, memory, and network usage in real-time.

### Persistent Logs

Chat logs are stored inside the container at `/app/chat_logs/`. To persist:

```yaml
# Add to docker-compose.yml
volumes:
  - ./chat_logs:/app/chat_logs
```

## Updating the Application

### Update Code

```bash
# Pull latest changes (if using Git)
git pull

# Or copy updated files
rsync -avz new_files/ /path/to/deployment/spear-chatbot-app/

# Rebuild and restart
./rebuild.sh
```

### Update Dependencies

Edit `requirements.txt` and rebuild:

```bash
nano requirements.txt
./rebuild.sh
```

## Backup and Restore

### Backup Configuration

```bash
# Backup .env file
cp .env .env.backup

# Backup chat logs (if using persistent volume)
tar -czf chat_logs_backup.tar.gz chat_logs/
```

### Restore Configuration

```bash
# Restore .env
cp .env.backup .env

# Restore chat logs
tar -xzf chat_logs_backup.tar.gz
```

## Performance Tuning

### Adjust Memory Limits

Edit `docker-compose.yml`:

```yaml
services:
  spear-chatbot:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

### Streamlit Configuration

Create `.streamlit/config.toml` for custom Streamlit settings:

```toml
[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

## Production Checklist

- [ ] API key configured in `.env`
- [ ] Docker and Docker Compose installed
- [ ] Container running and healthy
- [ ] Application accessible via browser
- [ ] HTTPS configured (if public-facing)
- [ ] Firewall rules configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy in place
- [ ] Documentation reviewed

## Support

For issues or questions:
- Check logs with `./logs.sh`
- Review this guide
- Check GitHub issues
- Verify Docker and network configuration

## License

[Specify your license]

## Acknowledgments

- NOAA-GFDL for SPEAR climate model data
- Anthropic for Claude AI
- Streamlit for the web framework
