# PDF Processor for extracting text from uploaded PDFs

import PyPDF2
import io
from typing import Optional

class PDFProcessor:
    """Handles PDF text extraction"""
    
    def __init__(self):
        pass
    
    def extract_text(self, uploaded_file) -> Optional[str]:
        """
        Extract text content from uploaded PDF file
        
        Args:
            uploaded_file: Streamlit UploadedFile object
        
        Returns:
            Extracted text as string, or None if extraction fails
        """
        try:
            # Read the uploaded file
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            
            # Extract text from all pages
            text_content = []
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                if text:
                    # Clean up the text
                    text = self._clean_text(text)
                    text_content.append(text)
            
            # Combine all pages
            full_text = "\n\n".join(text_content)
            
            return full_text if full_text.strip() else None
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and formatting
        
        Args:
            text: Raw extracted text
        
        Returns:
            Cleaned text
        """
        # Replace multiple spaces with single space
        text = ' '.join(text.split())
        
        # Replace multiple newlines with double newline
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        text = '\n'.join(cleaned_lines)
        
        return text
    
    def extract_metadata(self, uploaded_file) -> dict:
        """
        Extract PDF metadata
        
        Args:
            uploaded_file: Streamlit UploadedFile object
        
        Returns:
            Dictionary with metadata
        """
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            
            metadata = {
                "num_pages": len(pdf_reader.pages),
                "title": uploaded_file.name,
                "size_bytes": uploaded_file.size
            }
            
            # Try to get PDF info if available
            if pdf_reader.metadata:
                metadata.update({
                    "author": pdf_reader.metadata.get("/Author", "Unknown"),
                    "creation_date": pdf_reader.metadata.get("/CreationDate", "Unknown"),
                    "producer": pdf_reader.metadata.get("/Producer", "Unknown")
                })
            
            return metadata
            
        except Exception as e:
            return {"error": str(e)}
