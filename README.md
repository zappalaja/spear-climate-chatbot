# SPEAR Climate Chatbot

An AI-powered chatbot for exploring SPEAR (Seamless system for Prediction and EArth system Research) climate model data.

## Features

- 🌡️ **Direct SPEAR Data Access**: Query climate data from AWS S3 (historical and SSP5-8.5 scenarios)
- 📊 **Automatic Visualization**: Generate publication-quality plots with metadata
- 🤖 **Claude AI Integration**: Powered by Anthropic's Claude Sonnet 4.5
- 🔍 **Smart Size Management**: Automatic query validation and size checking
- 🌍 **Geographic Conversion**: Auto-converts longitude formats (-180/180 ↔ 0-360)
- 📚 **Expert Knowledge Base**: Built-in climate science terminology and SPEAR model info
- ⚡ **Confidence Assessment**: Self-assessment of response accuracy

## Quick Start

Python Virtual Environment

1. **Clone and setup**
   ```bash
   git clone https://github.com/zappalaja/spear-climate-chatbot.git
   cd spear-climate-chatbot
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**
   ```bash
   cp .env.template .env
   # Edit .env and add your Anthropic API key:
   # ANTHROPIC_API_KEY=your_api_key_here
   ```

4. **Run the application**
   ```bash
   streamlit run chatbot_app.py
   ```

5. **Access the chatbot**
   Open your browser to: http://localhost:8501

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

Get your API key from: https://console.anthropic.com/

### Customization

The chatbot's behavior can be customized by editing:

- **`controlled_vocabulary.py`**: Language policies, prohibited topics, terminology
- **`variable_definitions.py`**: Climate variable definitions and units
- **`spear_model_info.py`**: SPEAR model specifications and scenarios
- **`confidence_assessment.py`**: Confidence assessment criteria
- **`ai_config.py`**: Model settings, temperature, welcome message

See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for details.

## Podman Deployment

### Build the image

```bash
podman build -t spear-chatbot .
```

## Usage Examples

### Query Climate Data

```
"Show me temperature data for the Northeast US from 2020-2030"
"What is the precipitation trend in Europe for SSP5-8.5?"
"Plot sea surface temperature for the Pacific Ocean"
```

### Browse Available Data

```
"What variables are available in SPEAR?"
"List the ensemble members for historical scenario"
"Show me metadata for temperature data"
```

### Get Explanations

```
"What is SSP5-8.5?"
"Explain the difference between tas and tasmax"
"What are ensemble members?"
```


### Size Management

The chatbot automatically prevents queries that would exceed API token limits:

- **Maximum**: 200,000 tokens per request
- **Safe threshold**: 100,000 tokens (for data)
- **Automatic blocking**: Queries exceeding limits show alternatives
- **Suggestions**: Smaller regions, shorter time periods, or Python code

## System Requirements

### Minimum

- Python 3.11+
- 2GB RAM
- Internet connection (for S3 access)
- Anthropic API key

## Troubleshooting

### "ModuleNotFoundError"

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### "Invalid API key"

Check your `.env` file has the correct API key:
```bash
ANTHROPIC_API_KEY=...
```

### "Query too large" errors

The chatbot will show alternatives. Try:
- Smaller geographic region
- Shorter time period
- Request spatial averages

### Docker connection issues

Ensure port 8501 is available:
```bash
lsof -i :8501
```
