# SPEAR Climate Chatbot

An AI-powered chatbot for exploring SPEAR (Seamless system for Prediction and EArth system Research) climate model data from NOAA-GFDL.

## Features

- 🌡️ **Direct SPEAR Data Access**: Query climate data from AWS S3 (historical and SSP5-8.5 scenarios)
- 📊 **Automatic Visualization**: Generate publication-quality plots with metadata
- 🤖 **Claude AI Integration**: Powered by Anthropic's Claude Sonnet 4.5
- 🔍 **Smart Size Management**: Automatic query validation and size checking
- 🌍 **Geographic Conversion**: Auto-converts longitude formats (-180/180 ↔ 0-360)
- 📚 **Expert Knowledge Base**: Built-in climate science terminology and SPEAR model info
- ⚡ **Confidence Assessment**: Self-assessment of response accuracy

## Quick Start

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/spear-chatbot.git
   cd spear-chatbot
   ```

2. **Set up environment**
   ```bash
   cp .env.template .env
   # Edit .env and add your Anthropic API key
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up
   ```

4. **Access the chatbot**
   Open your browser to: http://localhost:8501

### Option 2: Python Virtual Environment

1. **Clone and setup**
   ```bash
   git clone https://github.com/YOUR_USERNAME/spear-chatbot.git
   cd spear-chatbot
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
   # ANTHROPIC_API_KEY=sk-ant-api03-...
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

## Docker Deployment

### Build the image

```bash
docker build -t spear-chatbot .
```

### Run the container

```bash
docker run -d \
  -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your_key_here \
  --name spear-chatbot \
  spear-chatbot
```

### Using Docker Compose

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
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

## Technical Details

### Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Claude AI      │  ← Knowledge Base (terminology, model info)
│  (Sonnet 4.5)   │  ← Tool Definitions (5 tools)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MCP Tools       │  ← Size validation
│ Wrapper         │  ← Coordinate conversion
└────────┬────────┘
         │
         ├──► browse_spear_directory()
         ├──► search_spear_variables()
         ├──► get_s3_file_metadata_only()
         ├──► query_netcdf_data()      ← Direct S3 access
         └──► create_plot()             ← Matplotlib
```

### Size Management

The chatbot automatically prevents queries that would exceed API token limits:

- **Maximum**: 200,000 tokens per request
- **Safe threshold**: 100,000 tokens (for data)
- **Automatic blocking**: Queries exceeding limits show alternatives
- **Suggestions**: Smaller regions, shorter time periods, or Python code

### Coordinate System

SPEAR uses **0-360 longitude** format:

- Input: `-140 to -50` (Americas)
- Auto-converts to: `220 to 310`
- No user intervention required!

## System Requirements

### Minimum

- Python 3.11+
- 2GB RAM
- Internet connection (for S3 access)
- Anthropic API key

### Docker

- Docker 20.10+
- Docker Compose 2.0+

## Project Structure

```
spear-chatbot-app/
├── chatbot_app.py              # Main Streamlit application
├── ai_config.py                # AI configuration and system prompt
├── claude_tools.py             # Tool definitions for Claude
├── mcp_tools_wrapper.py        # Tool execution with validation
├── knowledge_base_loader.py    # Loads all configuration
├── controlled_vocabulary.py    # Language policies
├── variable_definitions.py     # Climate variable definitions
├── spear_model_info.py         # SPEAR model information
├── confidence_assessment.py    # Confidence assessment logic
├── document_processor.py       # PDF/text document processing
├── response_size_estimator.py  # Query size validation
├── plotting_tool.py            # Matplotlib plotting
├── src/
│   └── spear_mcp/             # SPEAR MCP tools
│       ├── tools.py           # Directory/search tools
│       └── tools_nc.py        # NetCDF data tools
├── reference_documents/        # SPEAR documentation
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
└── README.md                   # This file
```

## Troubleshooting

### "ModuleNotFoundError"

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### "Invalid API key"

Check your `.env` file has the correct API key:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
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

## Data Attribution

This chatbot provides access to **SPEAR (Seamless system for Prediction and EArth system Research)** climate model data:

- **Developer**: NOAA Geophysical Fluid Dynamics Laboratory (GFDL)
- **Data Source**: AWS S3 (public bucket)
- **Scenarios**: Historical (1850-2014), SSP5-8.5 (2015-2100)
- **Resolution**: ~100km (SPEAR_MED)

**Citation**: Data from NOAA-GFDL SPEAR model. Users should cite appropriate SPEAR publications when using this data.

## License

[Specify your license here]

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation
- Review configuration guide

## Acknowledgments

- NOAA-GFDL for SPEAR climate model data
- Anthropic for Claude AI
- Streamlit for the web framework
