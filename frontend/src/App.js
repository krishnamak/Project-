import React, { useState, useEffect, useCallback } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [documents, setDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("all");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [stats, setStats] = useState({ total_documents: 0, file_type_distribution: {} });
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [searchOptions, setSearchOptions] = useState({
    fuzzy: true,
    boolean_mode: false,
    filters: {
      file_type: "",
      date_from: "",
      date_to: ""
    }
  });
  const [dragActive, setDragActive] = useState(false);

  // Load initial data
  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error("Error loading documents:", error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error loading stats:", error);
    }
  };

  const handleFileUpload = async (files) => {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
      setIsUploading(true);
      setUploadProgress(0);
      
      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await axios.post(`${API}/upload`, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          },
        });

        console.log("File uploaded successfully:", response.data);
        await loadDocuments();
        await loadStats();
      } catch (error) {
        console.error("Error uploading file:", error);
        alert(`Error uploading ${file.name}: ${error.response?.data?.detail || error.message}`);
      }
    }
    
    setIsUploading(false);
    setUploadProgress(0);
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files);
    }
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const searchRequest = {
        query: searchQuery,
        search_type: searchType,
        fuzzy: searchOptions.fuzzy,
        boolean_mode: searchOptions.boolean_mode,
        filters: Object.fromEntries(
          Object.entries(searchOptions.filters).filter(([_, value]) => value !== "")
        )
      };

      const response = await axios.post(`${API}/search`, searchRequest);
      setSearchResults(response.data.documents);
    } catch (error) {
      console.error("Error searching:", error);
      alert(`Search error: ${error.response?.data?.detail || error.message}`);
    }
    setIsSearching(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const viewDocument = async (documentId) => {
    try {
      const response = await axios.get(`${API}/document/${documentId}`);
      setSelectedDocument(response.data);
    } catch (error) {
      console.error("Error loading document:", error);
    }
  };

  const deleteDocument = async (documentId) => {
    if (window.confirm("Are you sure you want to delete this document?")) {
      try {
        await axios.delete(`${API}/document/${documentId}`);
        await loadDocuments();
        await loadStats();
        if (selectedDocument && selectedDocument.id === documentId) {
          setSelectedDocument(null);
        }
      } catch (error) {
        console.error("Error deleting document:", error);
        alert("Error deleting document");
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const highlightSearchTerm = (text, searchTerm) => {
    if (!searchTerm || !text) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.split(regex).map((part, index) =>
      regex.test(part) ? <mark key={index} className="bg-yellow-200">{part}</mark> : part
    );
  };

  return (
    <div
      className="min-h-screen bg-gray-50"
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Document Search System</h1>
                <p className="text-sm text-gray-600">Offline search for confidential documents</p>
              </div>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <span className="font-medium">{stats.total_documents}</span>
                <span>documents</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Sidebar - Upload & Stats */}
          <div className="lg:col-span-1 space-y-6">
            {/* Upload Section */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>
              
              <div className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
              }`}>
                {isUploading ? (
                  <div className="space-y-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-sm text-gray-600">Uploading and processing...</p>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <div>
                      <p className="text-sm text-gray-600">
                        <span className="font-medium text-blue-600 hover:text-blue-500 cursor-pointer">
                          Click to upload
                        </span>
                        {' '}or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">PDF, DOCX, or TXT files</p>
                    </div>
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.docx,.txt"
                      onChange={(e) => handleFileUpload(e.target.files)}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 cursor-pointer"
                    >
                      Select Files
                    </label>
                  </div>
                )}
              </div>
            </div>

            {/* Stats Section */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold mb-4">Statistics</h2>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Documents:</span>
                  <span className="font-medium">{stats.total_documents}</span>
                </div>
                {Object.entries(stats.file_type_distribution).map(([type, count]) => (
                  <div key={type} className="flex justify-between">
                    <span className="text-gray-600">{type} files:</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content - Search & Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Search Section */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Search documents by title, author, content, or keywords..."
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <button
                    onClick={handleSearch}
                    disabled={isSearching}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {isSearching ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    )}
                    <span>Search</span>
                  </button>
                </div>

                <div className="flex items-center space-x-4 text-sm">
                  <select
                    value={searchType}
                    onChange={(e) => setSearchType(e.target.value)}
                    className="border border-gray-300 rounded px-3 py-1"
                  >
                    <option value="all">All Fields</option>
                    <option value="title">Title Only</option>
                    <option value="author">Author Only</option>
                    <option value="publisher">Publisher Only</option>
                    <option value="content">Content Only</option>
                    <option value="keywords">Keywords Only</option>
                  </select>

                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={searchOptions.fuzzy}
                      onChange={(e) => setSearchOptions({...searchOptions, fuzzy: e.target.checked})}
                      className="rounded"
                    />
                    <span>Fuzzy Search</span>
                  </label>

                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={searchOptions.boolean_mode}
                      onChange={(e) => setSearchOptions({...searchOptions, boolean_mode: e.target.checked})}
                      className="rounded"
                    />
                    <span>Boolean Mode</span>
                  </label>

                  <button
                    onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    Advanced
                  </button>
                </div>

                {showAdvancedSearch && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">File Type</label>
                      <select
                        value={searchOptions.filters.file_type}
                        onChange={(e) => setSearchOptions({
                          ...searchOptions,
                          filters: {...searchOptions.filters, file_type: e.target.value}
                        })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                      >
                        <option value="">All Types</option>
                        <option value="PDF">PDF</option>
                        <option value="DOCX">Word</option>
                        <option value="TXT">Text</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">From Date</label>
                      <input
                        type="date"
                        value={searchOptions.filters.date_from}
                        onChange={(e) => setSearchOptions({
                          ...searchOptions,
                          filters: {...searchOptions.filters, date_from: e.target.value}
                        })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">To Date</label>
                      <input
                        type="date"
                        value={searchOptions.filters.date_to}
                        onChange={(e) => setSearchOptions({
                          ...searchOptions,
                          filters: {...searchOptions.filters, date_to: e.target.value}
                        })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Results Section */}
            <div className="bg-white rounded-lg shadow-sm border">
              {searchQuery && searchResults.length > 0 && (
                <div className="p-4 border-b">
                  <p className="text-sm text-gray-600">
                    Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
                  </p>
                </div>
              )}

              <div className="divide-y">
                {(searchQuery ? searchResults : documents).map((doc) => (
                  <div key={doc.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-medium text-gray-900 truncate">
                            {searchQuery ? highlightSearchTerm(doc.title, searchQuery) : doc.title}
                          </h3>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {doc.file_type}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 mb-3">
                          {doc.author && (
                            <div>
                              <span className="font-medium">Author: </span>
                              {searchQuery ? highlightSearchTerm(doc.author, searchQuery) : doc.author}
                            </div>
                          )}
                          {doc.publisher && (
                            <div>
                              <span className="font-medium">Publisher: </span>
                              {searchQuery ? highlightSearchTerm(doc.publisher, searchQuery) : doc.publisher}
                            </div>
                          )}
                          <div>
                            <span className="font-medium">Size: </span>
                            {formatFileSize(doc.file_size)}
                          </div>
                          <div>
                            <span className="font-medium">Uploaded: </span>
                            {new Date(doc.upload_date).toLocaleDateString()}
                          </div>
                        </div>

                        {doc.keywords.length > 0 && (
                          <div className="mb-3">
                            <span className="text-sm font-medium text-gray-700">Keywords: </span>
                            <div className="inline-flex flex-wrap gap-1 mt-1">
                              {doc.keywords.slice(0, 8).map((keyword, index) => (
                                <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                  {searchQuery ? highlightSearchTerm(keyword, searchQuery) : keyword}
                                </span>
                              ))}
                              {doc.keywords.length > 8 && (
                                <span className="text-xs text-gray-500">+{doc.keywords.length - 8} more</span>
                              )}
                            </div>
                          </div>
                        )}

                        <p className="text-sm text-gray-600 line-clamp-3">
                          {searchQuery ? highlightSearchTerm(doc.abstract, searchQuery) : doc.abstract}
                        </p>
                      </div>

                      <div className="ml-4 flex-shrink-0 space-x-2">
                        <button
                          onClick={() => viewDocument(doc.id)}
                          className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                        >
                          View
                        </button>
                        <button
                          onClick={() => deleteDocument(doc.id)}
                          className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {searchQuery && searchResults.length === 0 && !isSearching && (
                  <div className="p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No documents found</h3>
                    <p className="mt-1 text-sm text-gray-500">Try adjusting your search terms or filters.</p>
                  </div>
                )}

                {!searchQuery && documents.length === 0 && (
                  <div className="p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No documents uploaded</h3>
                    <p className="mt-1 text-sm text-gray-500">Upload your first document to get started.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Document Viewer Modal */}
      {selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl max-h-full w-full overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-semibold text-gray-900">{selectedDocument.title}</h2>
              <button
                onClick={() => setSelectedDocument(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 max-h-96 overflow-y-auto">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><strong>Author:</strong> {selectedDocument.author || 'N/A'}</div>
                  <div><strong>Publisher:</strong> {selectedDocument.publisher || 'N/A'}</div>
                  <div><strong>File Type:</strong> {selectedDocument.file_type}</div>
                  <div><strong>Size:</strong> {formatFileSize(selectedDocument.file_size)}</div>
                </div>
                {selectedDocument.keywords.length > 0 && (
                  <div>
                    <strong className="text-sm">Keywords:</strong>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedDocument.keywords.map((keyword, index) => (
                        <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <strong className="text-sm">Content:</strong>
                  <div className="mt-2 p-4 bg-gray-50 rounded-lg text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {selectedDocument.content || 'No content extracted'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Drag Overlay */}
      {dragActive && (
        <div className="fixed inset-0 bg-blue-500 bg-opacity-20 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 shadow-lg">
            <div className="text-center">
              <svg className="mx-auto h-16 w-16 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="mt-4 text-lg font-semibold text-gray-900">Drop files to upload</p>
              <p className="text-sm text-gray-600">PDF, DOCX, or TXT files</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;