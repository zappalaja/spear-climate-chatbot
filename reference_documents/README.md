# Reference Documents Folder

## Purpose

Place PDF files and other documentation about SPEAR models in this folder to provide the chatbot with additional context when forming responses.

## How It Works

When the chatbot starts, it will:
1. Scan this folder for PDF files
2. Extract text content from each PDF
3. Index the documents by topic/filename
4. Make summaries available to the chatbot as reference material

## Supported File Types

- **PDF files** (`.pdf`) - Preferred format for scientific papers, model documentation, user guides
- **Text files** (`.txt`) - Plain text documentation
- **Markdown files** (`.md`) - Formatted documentation

## What to Include

### Recommended Documents:

1. **SPEAR Model Documentation**
   - Official SPEAR technical reports
   - Model component descriptions (AM4, MOM6, SIS2, LM4)
   - Configuration and experiment design papers

2. **Scientific Publications**
   - SPEAR validation studies
   - Papers using SPEAR data
   - Climate science background relevant to SPEAR

3. **Data Documentation**
   - Variable definitions and conventions
   - Dataset descriptions
   - Quality control and validation reports

4. **User Guides**
   - Data access guides
   - Analysis tutorials
   - Best practices for using SPEAR data

### Example File Naming Convention:

Use descriptive names that help identify the content:

```
SPEAR_Technical_Documentation_2021.pdf
SPEAR_MED_Validation_Study.pdf
AM4_Atmospheric_Model_Description.pdf
SSP585_Scenario_Details.pdf
SPEAR_Variable_Glossary.pdf
```

## File Organization (Optional)

You can organize files into subdirectories:

```
reference_documents/
├── model_documentation/
│   ├── SPEAR_Technical_Report.pdf
│   └── Component_Models.pdf
├── scientific_papers/
│   ├── Validation_Studies.pdf
│   └── Application_Papers.pdf
├── data_guides/
│   ├── Variable_Conventions.pdf
│   └── Data_Access_Guide.pdf
└── README.md (this file)
```

## Current Status

**Documents in folder:** (will be scanned at startup)

The chatbot will display a list of loaded documents when you start a conversation.

## How the Chatbot Uses These Documents

The chatbot will:
- **Reference documents** when answering questions about SPEAR
- **Cite specific sources** when using information from PDFs
- **Increase confidence** in responses backed by official documentation
- **Provide more detailed explanations** using document context

## Document Processing

Documents are processed as follows:
1. **Text extraction**: PDFs are converted to text
2. **Chunking**: Long documents are split into manageable sections
3. **Indexing**: Documents are indexed by topic/keywords
4. **Summary generation**: Key information is summarized for quick reference
5. **Integration**: Summaries are added to the chatbot's knowledge base

## Privacy and Security

- Documents in this folder are **local only** - they are not uploaded anywhere
- Processing happens on your machine
- Documents are loaded into memory at startup only

## Limitations

- **Token limits**: Very large documents may be summarized rather than included in full
- **Processing time**: First startup with many PDFs may take longer
- **File size**: Keep individual PDFs under 50MB for optimal performance
- **OCR**: Scanned PDFs (images) may not extract well - prefer text-based PDFs

## Adding New Documents

1. Drop PDF files into this folder (or subfolders)
2. Restart the Streamlit app to reload documents
3. The chatbot will automatically detect and process new files

## Removing Documents

1. Delete the PDF file from this folder
2. Restart the Streamlit app
3. The chatbot will no longer have access to that document

## Examples of Good Documents to Include

### SPEAR-Specific:
- SPEAR Large Ensemble documentation
- SPEAR model intercomparison studies
- GFDL model description papers
- SPEAR data portal user guides

### General Climate Science:
- IPCC report chapters (relevant sections)
- Climate variable definitions (CF conventions)
- Climate scenario descriptions (SSP narratives)
- Ensemble methodology papers

### Technical:
- NetCDF file format specifications
- AWS S3 data access guides
- Python analysis examples

## Troubleshooting

**Problem:** PDF not being processed
- **Solution**: Ensure it's a text-based PDF (not a scanned image)
- Try converting to .txt format

**Problem:** Chatbot not using document information
- **Solution**: Check that the document was loaded (look for confirmation message at startup)
- Try asking more specific questions related to the document content

**Problem:** Slow startup
- **Solution**: Too many or very large PDFs. Consider:
  - Removing less relevant documents
  - Splitting large PDFs into smaller sections
  - Moving to subdirectories and selecting which to load

## Future Enhancements

Planned features:
- [ ] Semantic search across documents
- [ ] Document similarity matching
- [ ] Automatic citation generation
- [ ] Document versioning
- [ ] Interactive document browser in the app

## Questions?

See CONFIGURATION_GUIDE.md for general configuration help.
