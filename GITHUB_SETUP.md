# GitHub Repository Setup Guide

Guide for creating and uploading the SPEAR Climate Chatbot to GitHub.

## Prerequisites

- Git installed on your system
- GitHub account
- SSH key configured (or use HTTPS)

## Step 1: Create GitHub Repository

### Via GitHub Website

1. Go to https://github.com/new
2. Enter repository details:
   - **Name**: `spear-climate-chatbot` (or your preferred name)
   - **Description**: "AI-powered chatbot for exploring SPEAR climate model data"
   - **Visibility**: Public or Private
   - **DO NOT** initialize with README (we already have one)
3. Click "Create repository"

### Via GitHub CLI (Alternative)

```bash
gh repo create spear-climate-chatbot --public --description "AI-powered chatbot for exploring SPEAR climate model data"
```

## Step 2: Initialize Git Repository

Navigate to the chatbot directory:

```bash
cd spear-chatbot-app/
```

Initialize Git (if not already initialized):

```bash
git init
```

## Step 3: Verify .gitignore

The `.gitignore` file should already exclude sensitive files:

```bash
cat .gitignore
```

Should include:
- `.env` (CRITICAL - protects API key)
- `__pycache__/`
- `chat_logs/`
- `*.log`
- `reference_documents/*.pdf` (optional, PDFs can be large)

## Step 4: Stage Files

```bash
# Add all files
git add .

# Verify what will be committed (make sure .env is NOT listed)
git status
```

**IMPORTANT**: Verify `.env` is NOT in the staged files!

## Step 5: Create Initial Commit

```bash
git commit -m "Initial commit: SPEAR Climate Chatbot

- Streamlit web application with Claude AI integration
- Direct S3 access to SPEAR climate data
- Automatic query size validation and coordinate conversion
- Docker containerization with deployment scripts
- Comprehensive configuration system
- Reference documentation and PDF processing"
```

## Step 6: Add Remote and Push

Replace `YOUR_USERNAME` with your GitHub username:

```bash
# Add remote
git remote add origin git@github.com:YOUR_USERNAME/spear-climate-chatbot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

If using HTTPS instead:

```bash
git remote add origin https://github.com/YOUR_USERNAME/spear-climate-chatbot.git
git push -u origin main
```

## Step 7: Verify Upload

Visit your repository on GitHub:
```
https://github.com/YOUR_USERNAME/spear-climate-chatbot
```

Verify:
- [ ] README.md displays correctly
- [ ] `.env` is NOT present (only `.env.template`)
- [ ] All Python files are present
- [ ] Docker files are present
- [ ] `.gitignore` is working

## Step 8: Add Repository Topics (Optional)

On GitHub, click "Settings" → scroll to "Topics" and add:
- `climate-science`
- `chatbot`
- `claude-ai`
- `streamlit`
- `docker`
- `python`
- `noaa`
- `gfdl`
- `spear-model`

## Step 9: Create Release (Optional)

Create a release for version tracking:

```bash
# Tag the current commit
git tag -a v1.0.0 -m "Version 1.0.0 - Initial release"
git push origin v1.0.0
```

Then on GitHub:
1. Go to "Releases" → "Create a new release"
2. Select tag `v1.0.0`
3. Add release notes
4. Publish release

## Step 10: Update README with Correct URL

Edit `README.md` and replace placeholder URLs:

```bash
nano README.md
```

Find and replace:
```
YOUR_USERNAME → your-actual-username
```

Commit and push:

```bash
git add README.md
git commit -m "Update README with correct repository URL"
git push
```

## Repository Structure on GitHub

Your repository should look like:

```
spear-climate-chatbot/
├── .gitignore
├── .env.template              ✅ Template (safe)
├── README.md
├── DEPLOYMENT.md
├── GITHUB_SETUP.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start.sh
├── stop.sh
├── logs.sh
├── rebuild.sh
├── chatbot_app.py
├── ai_config.py
├── claude_tools.py
├── mcp_tools_wrapper.py
├── knowledge_base_loader.py
├── controlled_vocabulary.py
├── variable_definitions.py
├── spear_model_info.py
├── confidence_assessment.py
├── document_processor.py
├── response_size_estimator.py
├── plotting_tool.py
├── src/
│   └── spear_mcp/
│       ├── __init__.py
│       ├── tools.py
│       └── tools_nc.py
└── reference_documents/
    ├── README.md
    └── SPEAR_Quick_Reference.txt
```

## Security Checklist

Before pushing to GitHub:

- [ ] `.env` is in `.gitignore` and NOT staged
- [ ] No API keys in any files
- [ ] No sensitive credentials in code
- [ ] `.env.template` has placeholder text only
- [ ] No personal data in chat logs

## Common Issues

### "Support for password authentication was removed"

**Solution**: Use SSH key or personal access token

```bash
# Generate SSH key (if needed)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub: Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/id_ed25519.pub
```

### "Repository already exists"

**Solution**: Skip repository creation and add remote directly

```bash
git remote add origin git@github.com:YOUR_USERNAME/spear-climate-chatbot.git
git push -u origin main
```

### ".env accidentally committed"

**CRITICAL FIX**:

```bash
# Remove from Git history
git rm --cached .env

# Commit the removal
git commit -m "Remove .env from version control"

# Force push (if already pushed)
git push -f origin main

# IMMEDIATELY rotate your API key at https://console.anthropic.com/
```

## Collaboration Setup

### Branch Protection

On GitHub:
1. Settings → Branches → Add branch protection rule
2. Branch name pattern: `main`
3. Enable:
   - Require pull request before merging
   - Require status checks to pass

### Issue Templates

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug Report
about: Report a bug in the SPEAR Climate Chatbot
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Docker version: [e.g., 20.10.23]
- Browser: [e.g., Chrome 120]
```

## Cloning and Testing

Test that others can clone and deploy:

```bash
# Clone in a new directory
cd /tmp
git clone https://github.com/YOUR_USERNAME/spear-climate-chatbot.git
cd spear-climate-chatbot

# Configure API key
cp .env.template .env
nano .env

# Test deployment
./start.sh
```

## Next Steps

After GitHub setup:

1. **Add CI/CD** (optional): GitHub Actions for automated testing
2. **Add badges** to README: build status, Docker image, etc.
3. **Enable Discussions**: For community Q&A
4. **Create Wiki**: Additional documentation
5. **Link to DockerHub** (optional): Publish pre-built images

## Maintenance

### Regular Updates

```bash
# Make changes locally
nano chatbot_app.py

# Commit and push
git add .
git commit -m "Description of changes"
git push
```

### Tagging Versions

```bash
# Create new version tag
git tag -a v1.1.0 -m "Version 1.1.0 - Feature XYZ"
git push origin v1.1.0
```

## License

Consider adding a LICENSE file:

```bash
# Choose license at https://choosealicense.com/
# Popular options:
# - MIT License (permissive)
# - Apache 2.0 (permissive with patent grant)
# - GPL v3 (copyleft)

# Add LICENSE file
touch LICENSE
git add LICENSE
git commit -m "Add LICENSE"
git push
```

## Documentation

Your repository now has comprehensive documentation:

1. **README.md** - Overview, quick start, features
2. **DEPLOYMENT.md** - Docker deployment guide
3. **GITHUB_SETUP.md** - This file
4. **reference_documents/** - SPEAR-specific documentation

Users can deploy by simply:
```bash
git clone [your-repo-url]
cd spear-climate-chatbot
cp .env.template .env
# Add API key to .env
./start.sh
```

## Complete!

Your SPEAR Climate Chatbot is now:
- ✅ Version controlled with Git
- ✅ Hosted on GitHub
- ✅ Ready for collaboration
- ✅ Documented for deployment
- ✅ Secure (no exposed secrets)
