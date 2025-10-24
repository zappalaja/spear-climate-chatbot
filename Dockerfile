# SPEAR Climate Chatbot Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY chatbot_app.py .
COPY ai_config.py .
COPY claude_tools.py .
COPY mcp_tools_wrapper.py .
COPY knowledge_base_loader.py .
COPY controlled_vocabulary.py .
COPY variable_definitions.py .
COPY spear_model_info.py .
COPY confidence_assessment.py .
COPY document_processor.py .
COPY response_size_estimator.py .
COPY plotting_tool.py .

# Copy reference documents
COPY reference_documents/ ./reference_documents/

# Create .env template
RUN echo "ANTHROPIC_API_KEY=your_api_key_here" > .env.template

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "chatbot_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
