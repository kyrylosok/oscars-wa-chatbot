# Data Directory

This directory contains the PDF documents that will be processed by the chatbot.

## Setup

1. Place your product PDF file in this directory
2. The default filename should be `product.pdf`
3. You can change the filename by updating the `PDF_FILE_PATH` environment variable

## Supported Formats

- PDF files (.pdf)
- The PDF should contain text content (not just images)
- For best results, use PDFs with clear text structure

## Example

```
data/
├── product.pdf          # Your main product documentation
├── manual.pdf           # Additional documentation (if needed)
└── README.md           # This file
```

## Notes

- The system will automatically process the PDF on startup
- Processing may take a few minutes for large documents
- The processed data is stored in the `storage/faiss_index/` directory
- If you update the PDF, you can reindex using the `/api/reindex` endpoint 