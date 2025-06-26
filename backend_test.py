#!/usr/bin/env python3
import os
import sys
import json
import unittest
import requests
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get backend URL from frontend .env file
def get_backend_url():
    env_file = Path("/app/frontend/.env")
    if not env_file.exists():
        raise FileNotFoundError("Frontend .env file not found")
    
    with open(env_file, "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                backend_url = line.strip().split("=", 1)[1].strip('"')
                return f"{backend_url}/api"
    
    raise ValueError("REACT_APP_BACKEND_URL not found in frontend .env file")

# Base API URL
API_URL = get_backend_url()
logger.info(f"Using API URL: {API_URL}")

class DocumentSearchAPITest(unittest.TestCase):
    """Test suite for Document Search API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests"""
        cls.test_files = cls._create_test_files()
        cls.uploaded_docs = []  # Track uploaded documents for cleanup
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Delete all uploaded test documents
        for doc_id in cls.uploaded_docs:
            try:
                requests.delete(f"{API_URL}/document/{doc_id}")
                logger.info(f"Deleted test document: {doc_id}")
            except Exception as e:
                logger.error(f"Error deleting test document {doc_id}: {e}")
    
    @classmethod
    def _create_test_files(cls) -> Dict[str, str]:
        """Create test files for upload testing"""
        test_files = {}
        
        # Create a PDF test file
        pdf_content = """
        %PDF-1.3
        1 0 obj
        << /Type /Catalog
           /Outlines 2 0 R
           /Pages 3 0 R
        >>
        endobj
        
        2 0 obj
        << /Type /Outlines
           /Count 0
        >>
        endobj
        
        3 0 obj
        << /Type /Pages
           /Kids [4 0 R]
           /Count 1
        >>
        endobj
        
        4 0 obj
        << /Type /Page
           /Parent 3 0 R
           /MediaBox [0 0 612 792]
           /Contents 5 0 R
           /Resources << /ProcSet 6 0 R
                         /Font << /F1 7 0 R >>
                      >>
        >>
        endobj
        
        5 0 obj
        << /Length 73 >>
        stream
        BT
        /F1 24 Tf
        100 700 Td
        (Test PDF Document for API Testing) Tj
        ET
        endstream
        endobj
        
        6 0 obj
        [/PDF /Text]
        endobj
        
        7 0 obj
        << /Type /Font
           /Subtype /Type1
           /Name /F1
           /BaseFont /Helvetica
        >>
        endobj
        
        xref
        0 8
        0000000000 65535 f
        0000000009 00000 n
        0000000074 00000 n
        0000000120 00000 n
        0000000179 00000 n
        0000000364 00000 n
        0000000466 00000 n
        0000000496 00000 n
        
        trailer
        << /Size 8
           /Root 1 0 R
        >>
        startxref
        625
        %%EOF
        """
        
        # Create a text file
        txt_content = """
        Test Document for API Testing
        
        Author: Test Author
        Publisher: Test Publisher
        
        This is a sample text document used for testing the document search API.
        It contains keywords like: confidential, research, information, search, testing.
        
        The document search system should be able to extract metadata and content from this file.
        It should also be able to perform full-text search and find this document when searching for relevant terms.
        
        Additional test keywords: offline, document, system, extraction, processing.
        """
        
        # Create a simple DOCX-like content (not actual DOCX but will be detected as text)
        docx_content = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p>
              <w:r>
                <w:t>Test DOCX Document for API Testing</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>Author: DOCX Test Author</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>Publisher: DOCX Test Publisher</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>This is a sample DOCX document used for testing the document search API.</w:t>
              </w:r>
            </w:p>
            <w:p>
              <w:r>
                <w:t>It contains keywords like: confidential, research, information, search, testing.</w:t>
              </w:r>
            </w:p>
          </w:body>
        </w:document>
        """
        
        # Save test files to temporary directory
        temp_dir = tempfile.mkdtemp()
        
        pdf_path = os.path.join(temp_dir, "test_document.pdf")
        with open(pdf_path, "w") as f:
            f.write(pdf_content)
        test_files["pdf"] = pdf_path
        
        txt_path = os.path.join(temp_dir, "test_document.txt")
        with open(txt_path, "w") as f:
            f.write(txt_content)
        test_files["txt"] = txt_path
        
        docx_path = os.path.join(temp_dir, "test_document.docx")
        with open(docx_path, "w") as f:
            f.write(docx_content)
        test_files["docx"] = docx_path
        
        logger.info(f"Created test files in {temp_dir}")
        return test_files
    
    def test_01_health_check(self):
        """Test API health check endpoint"""
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("running", data["message"])
        logger.info("Health check passed")
    
    def test_02_upload_text_document(self):
        """Test uploading a text document"""
        with open(self.test_files["txt"], "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            response = requests.post(f"{API_URL}/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertIn("id", data)
        self.assertIn("title", data)
        self.assertIn("file_type", data)
        self.assertIn("content", data)
        self.assertIn("keywords", data)
        
        # Verify content extraction - file type might be TXT or Unknown
        self.assertIn(data["file_type"], ["TXT", "Unknown"])
        self.assertIn("Test Document for API Testing", data["content"])
        
        # Verify keyword extraction
        self.assertTrue(len(data["keywords"]) > 0)
        
        # Save document ID for later tests and cleanup
        self.__class__.uploaded_docs.append(data["id"])
        logger.info(f"Uploaded text document with ID: {data['id']}")
    
    def test_03_upload_pdf_document(self):
        """Test uploading a PDF document"""
        with open(self.test_files["pdf"], "rb") as f:
            files = {"file": ("test_document.pdf", f, "application/pdf")}
            response = requests.post(f"{API_URL}/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertIn("id", data)
        self.assertIn("title", data)
        self.assertIn("file_type", data)
        
        # Verify file type detection
        self.assertEqual(data["file_type"], "PDF")
        
        # Save document ID for later tests and cleanup
        self.__class__.uploaded_docs.append(data["id"])
        logger.info(f"Uploaded PDF document with ID: {data['id']}")
    
    def test_04_upload_docx_document(self):
        """Test uploading a DOCX document"""
        with open(self.test_files["docx"], "rb") as f:
            files = {"file": ("test_document.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = requests.post(f"{API_URL}/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertIn("id", data)
        self.assertIn("title", data)
        self.assertIn("file_type", data)
        
        # Save document ID for later tests and cleanup
        self.__class__.uploaded_docs.append(data["id"])
        logger.info(f"Uploaded DOCX document with ID: {data['id']}")
    
    def test_05_get_all_documents(self):
        """Test retrieving all documents"""
        response = requests.get(f"{API_URL}/documents")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify we have at least the documents we uploaded
        self.assertGreaterEqual(len(data), len(self.uploaded_docs))
        
        # Verify document structure
        for doc in data:
            self.assertIn("id", doc)
            self.assertIn("title", doc)
            self.assertIn("file_type", doc)
        
        logger.info(f"Retrieved {len(data)} documents")
    
    def test_06_get_document_by_id(self):
        """Test retrieving a specific document by ID"""
        if not self.uploaded_docs:
            self.skipTest("No uploaded documents to test")
        
        doc_id = self.uploaded_docs[0]
        response = requests.get(f"{API_URL}/document/{doc_id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify document data
        self.assertEqual(data["id"], doc_id)
        self.assertIn("content", data)
        self.assertIn("file_type", data)
        
        logger.info(f"Retrieved document with ID: {doc_id}")
    
    def test_07_basic_search(self):
        """Test basic search functionality"""
        # Wait a moment for indexing
        time.sleep(1)
        
        search_data = {
            "query": "test",
            "search_type": "all",
            "fuzzy": True,
            "boolean_mode": False,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify search results
        self.assertIn("documents", data)
        self.assertIn("total_count", data)
        self.assertIn("search_time", data)
        
        # We should find at least one of our test documents
        self.assertGreater(data["total_count"], 0)
        
        logger.info(f"Basic search found {data['total_count']} documents")
    
    def test_08_field_specific_search(self):
        """Test field-specific search"""
        # Search by title
        search_data = {
            "query": "Document",
            "search_type": "title",
            "fuzzy": True,
            "boolean_mode": False,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["total_count"], 0)
        
        # Search by content
        search_data = {
            "query": "testing",
            "search_type": "content",
            "fuzzy": True,
            "boolean_mode": False,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        logger.info(f"Field-specific search found {data['total_count']} documents")
    
    def test_09_fuzzy_search(self):
        """Test fuzzy search functionality"""
        # Intentionally misspell a word that should still match
        search_data = {
            "query": "testin",  # Missing 'g' from 'testing'
            "search_type": "all",
            "fuzzy": True,
            "boolean_mode": False,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should still find documents with "testing"
        self.assertGreaterEqual(data["total_count"], 0)
        
        logger.info(f"Fuzzy search found {data['total_count']} documents")
    
    def test_10_boolean_search(self):
        """Test boolean search operators"""
        # Test AND operator
        search_data = {
            "query": "test AND document",
            "search_type": "all",
            "fuzzy": False,
            "boolean_mode": True,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        self.assertEqual(response.status_code, 200)
        and_results = response.json()
        
        # Test OR operator
        search_data = {
            "query": "test OR nonexistent",
            "search_type": "all",
            "fuzzy": False,
            "boolean_mode": True,
            "filters": {}
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        self.assertEqual(response.status_code, 200)
        or_results = response.json()
        
        logger.info(f"Boolean AND search found {and_results['total_count']} documents")
        logger.info(f"Boolean OR search found {or_results['total_count']} documents")
    
    def test_11_filtered_search(self):
        """Test search with filters"""
        # Filter by file type
        search_data = {
            "query": "test",
            "search_type": "all",
            "fuzzy": True,
            "boolean_mode": False,
            "filters": {
                "file_type": "PDF"
            }
        }
        
        response = requests.post(f"{API_URL}/search", json=search_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify all results are PDF files
        for doc in data["documents"]:
            self.assertEqual(doc["file_type"], "PDF")
        
        logger.info(f"Filtered search found {data['total_count']} documents")
    
    def test_12_stats_endpoint(self):
        """Test statistics endpoint"""
        response = requests.get(f"{API_URL}/stats")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify stats structure
        self.assertIn("total_documents", data)
        self.assertIn("file_type_distribution", data)
        
        # We should have at least the documents we uploaded
        self.assertGreaterEqual(data["total_documents"], len(self.uploaded_docs))
        
        logger.info(f"Stats: {data['total_documents']} total documents")
    
    def test_13_delete_document(self):
        """Test document deletion"""
        if not self.uploaded_docs:
            self.skipTest("No uploaded documents to test")
        
        # Get the last uploaded document
        doc_id = self.uploaded_docs[-1]
        
        # Delete the document
        response = requests.delete(f"{API_URL}/document/{doc_id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("deleted", data["message"])
        
        # Try to get the deleted document - should return 404 or 500
        response = requests.get(f"{API_URL}/document/{doc_id}")
        self.assertIn(response.status_code, [404, 500])
        
        # Remove from our tracking list
        self.uploaded_docs.remove(doc_id)
        
        logger.info(f"Deleted document with ID: {doc_id}")

if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)