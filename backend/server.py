from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import aiofiles
import PyPDF2
from docx import Document
import magic
from fuzzywuzzy import fuzz, process
import re
import json
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Ensure upload directory exists
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Document Models
class DocumentMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    author: str = ""
    publisher: str = ""
    keywords: List[str] = []
    file_type: str
    file_size: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    content: str = ""
    file_path: str = ""
    abstract: str = ""

class SearchRequest(BaseModel):
    query: str
    search_type: str = "all"  # all, title, author, publisher, content, keywords
    fuzzy: bool = True
    boolean_mode: bool = False
    filters: Dict[str, Any] = {}

class SearchResult(BaseModel):
    documents: List[DocumentMetadata]
    total_count: int
    search_time: float

# Document processing functions
def extract_pdf_content(file_path: str) -> tuple[str, Dict[str, Any]]:
    """Extract text content and metadata from PDF"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract metadata
            metadata = {}
            if pdf_reader.metadata:
                metadata = {
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'creator': pdf_reader.metadata.get('/Creator', ''),
                    'producer': pdf_reader.metadata.get('/Producer', ''),
                }
            
            # Extract text content
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
            
            return content.strip(), metadata
    except Exception as e:
        logging.error(f"Error extracting PDF content: {e}")
        return "", {}

def extract_docx_content(file_path: str) -> tuple[str, Dict[str, Any]]:
    """Extract text content and metadata from DOCX"""
    try:
        doc = Document(file_path)
        
        # Extract core properties
        props = doc.core_properties
        metadata = {
            'title': props.title or '',
            'author': props.author or '',
            'creator': props.creator or '',
            'keywords': props.keywords or '',
        }
        
        # Extract text content
        content = ""
        for paragraph in doc.paragraphs:
            content += paragraph.text + "\n"
        
        return content.strip(), metadata
    except Exception as e:
        logging.error(f"Error extracting DOCX content: {e}")
        return "", {}

def extract_text_content(file_path: str) -> tuple[str, Dict[str, Any]]:
    """Extract content from text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content.strip(), {}
    except Exception as e:
        logging.error(f"Error extracting text content: {e}")
        return "", {}

def process_document(file_path: str, filename: str) -> DocumentMetadata:
    """Process uploaded document and extract metadata"""
    file_size = os.path.getsize(file_path)
    
    # Detect file type using file extension
    file_extension = os.path.splitext(os.path.basename(file_path))[1].lower()
    
    if file_extension == '.pdf':
        file_type = "PDF"
    elif file_extension == '.docx':
        file_type = "DOCX"
    elif file_extension == '.txt':
        file_type = "TXT"
    else:
        # Default to TXT for unknown types
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                f.read(1024)  # Try to read as text
                file_type = "TXT"
            except:
                file_type = "Unknown"
    
    content = ""
    extracted_metadata = {}
    
    # Extract content based on file type
    if 'pdf' in file_type.lower():
        content, extracted_metadata = extract_pdf_content(file_path)
        file_type = "PDF"
    elif 'word' in file_type.lower() or 'officedocument' in file_type.lower():
        content, extracted_metadata = extract_docx_content(file_path)
        file_type = "DOCX"
    elif 'text' in file_type.lower():
        content, extracted_metadata = extract_text_content(file_path)
        file_type = "TXT"
    else:
        # Try to read as text anyway
        content, extracted_metadata = extract_text_content(file_path)
        file_type = "Unknown"
    
    # Extract keywords from content using simple approach
    keywords = extract_keywords(content)
    
    # Create document metadata
    doc_metadata = DocumentMetadata(
        title=extracted_metadata.get('title', filename) or filename,
        author=extracted_metadata.get('author', ''),
        publisher=extracted_metadata.get('creator', ''),
        keywords=keywords,
        file_type=file_type,
        file_size=file_size,
        content=content,
        file_path=file_path,
        abstract=content[:500] + "..." if len(content) > 500 else content
    )
    
    return doc_metadata

def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """Extract keywords from text using simple frequency analysis"""
    if not text:
        return []
    
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Common stop words to filter out
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'from', 'into', 'onto', 'upon', 'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond', 'during', 'except', 'inside', 'outside', 'through', 'throughout', 'until', 'within', 'without'}
    
    # Filter out stop words and count frequency
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top keywords
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in keywords[:max_keywords]]

def search_documents(query: str, search_type: str = "all", fuzzy: bool = True, boolean_mode: bool = False, filters: Dict = None) -> List[Dict]:
    """Search documents with various options"""
    # This is a simplified search - in production, you'd use proper search engines
    search_results = []
    
    # For now, return empty - we'll implement after database setup
    return search_results

# API Routes
@api_router.post("/upload", response_model=DocumentMetadata)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process document
        doc_metadata = process_document(str(file_path), file.filename)
        
        # Store in database
        await db.documents.insert_one(doc_metadata.dict())
        
        # Create text index for search
        await db.documents.create_index([
            ("title", "text"),
            ("author", "text"),
            ("publisher", "text"),
            ("content", "text"),
            ("keywords", "text")
        ])
        
        logging.info(f"Document uploaded and processed: {file.filename}")
        return doc_metadata
        
    except Exception as e:
        logging.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@api_router.post("/search", response_model=SearchResult)
async def search_documents_api(search_request: SearchRequest):
    """Search documents with advanced options"""
    start_time = datetime.now()
    
    try:
        query = search_request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        # Build MongoDB query
        search_conditions = []
        
        if search_request.boolean_mode:
            # Handle boolean search (simplified)
            try:
                if " AND " in query:
                    terms = query.split(" AND ")
                    for term in terms:
                        search_conditions.append({"$text": {"$search": term.strip()}})
                elif " OR " in query:
                    terms = query.split(" OR ")
                    or_conditions = [{"$text": {"$search": term.strip()}} for term in terms]
                    search_conditions.append({"$or": or_conditions})
                else:
                    search_conditions.append({"$text": {"$search": query}})
            except Exception as e:
                logging.error(f"Boolean search error: {e}")
                # Fallback to regular search
                search_conditions.append({"$text": {"$search": query}})
        else:
            # Regular search
            if search_request.search_type == "all":
                search_conditions.append({"$text": {"$search": query}})
            elif search_request.search_type == "title":
                if search_request.fuzzy:
                    search_conditions.append({"title": {"$regex": query, "$options": "i"}})
                else:
                    search_conditions.append({"title": {"$regex": f"^{query}$", "$options": "i"}})
            elif search_request.search_type == "author":
                if search_request.fuzzy:
                    search_conditions.append({"author": {"$regex": query, "$options": "i"}})
                else:
                    search_conditions.append({"author": {"$regex": f"^{query}$", "$options": "i"}})
            elif search_request.search_type == "publisher":
                if search_request.fuzzy:
                    search_conditions.append({"publisher": {"$regex": query, "$options": "i"}})
                else:
                    search_conditions.append({"publisher": {"$regex": f"^{query}$", "$options": "i"}})
            elif search_request.search_type == "content":
                search_conditions.append({"content": {"$regex": query, "$options": "i"}})
            elif search_request.search_type == "keywords":
                search_conditions.append({"keywords": {"$in": [query]}})
        
        # Apply filters
        if search_request.filters:
            if "file_type" in search_request.filters:
                search_conditions.append({"file_type": search_request.filters["file_type"]})
            if "date_from" in search_request.filters:
                search_conditions.append({"upload_date": {"$gte": datetime.fromisoformat(search_request.filters["date_from"])}})
            if "date_to" in search_request.filters:
                search_conditions.append({"upload_date": {"$lte": datetime.fromisoformat(search_request.filters["date_to"])}})
        
        # Combine conditions
        if search_conditions:
            final_query = {"$and": search_conditions} if len(search_conditions) > 1 else search_conditions[0]
        else:
            final_query = {}
        
        # Execute search
        cursor = db.documents.find(final_query)
        documents = await cursor.to_list(length=1000)
        
        # Convert to DocumentMetadata objects
        result_docs = []
        for doc in documents:
            # Remove MongoDB _id for JSON serialization
            if '_id' in doc:
                del doc['_id']
            result_docs.append(DocumentMetadata(**doc))
        
        # Apply fuzzy matching if enabled and no results found
        if search_request.fuzzy and not result_docs and search_request.search_type != "content":
            # Get all documents and apply fuzzy matching
            all_docs = await db.documents.find().to_list(length=1000)
            fuzzy_matches = []
            
            for doc in all_docs:
                if '_id' in doc:
                    del doc['_id']
                
                score = 0
                if search_request.search_type in ["all", "title"]:
                    score = max(score, fuzz.partial_ratio(query.lower(), doc.get('title', '').lower()))
                if search_request.search_type in ["all", "author"]:
                    score = max(score, fuzz.partial_ratio(query.lower(), doc.get('author', '').lower()))
                if search_request.search_type in ["all", "publisher"]:
                    score = max(score, fuzz.partial_ratio(query.lower(), doc.get('publisher', '').lower()))
                
                if score > 60:  # Threshold for fuzzy matching
                    fuzzy_matches.append((DocumentMetadata(**doc), score))
            
            # Sort by score and return top matches
            fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
            result_docs = [match[0] for match in fuzzy_matches[:50]]
        
        end_time = datetime.now()
        search_time = (end_time - start_time).total_seconds()
        
        return SearchResult(
            documents=result_docs,
            total_count=len(result_docs),
            search_time=search_time
        )
        
    except Exception as e:
        logging.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@api_router.get("/documents", response_model=List[DocumentMetadata])
async def get_all_documents():
    """Get all uploaded documents"""
    try:
        documents = await db.documents.find().to_list(length=1000)
        result_docs = []
        for doc in documents:
            if '_id' in doc:
                del doc['_id']
            result_docs.append(DocumentMetadata(**doc))
        return result_docs
    except Exception as e:
        logging.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

@api_router.get("/document/{document_id}")
async def get_document_content(document_id: str):
    """Get full document content"""
    try:
        document = await db.documents.find_one({"id": document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if '_id' in document:
            del document['_id']
        
        return DocumentMetadata(**document)
    except Exception as e:
        logging.error(f"Error fetching document content: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching document: {str(e)}")

@api_router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        # First check if document exists
        document = await db.documents.find_one({"id": document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Then delete it
        result = await db.documents.delete_one({"id": document_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logging.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@api_router.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        total_docs = await db.documents.count_documents({})
        
        # Get file type distribution
        pipeline = [
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}}
        ]
        file_types = await db.documents.aggregate(pipeline).to_list(length=None)
        
        return {
            "total_documents": total_docs,
            "file_type_distribution": {item["_id"]: item["count"] for item in file_types}
        }
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

# Health check
@api_router.get("/")
async def root():
    return {"message": "Document Search API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()