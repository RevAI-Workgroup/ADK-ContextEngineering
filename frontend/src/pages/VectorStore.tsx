/**
 * Vector Store Monitoring Page
 *
 * Displays ChromaDB status, statistics, and allows document management
 */

import React, { useState, useEffect } from 'react';
import {
  getVectorStoreStats,
  searchVectorStore,
  clearVectorStore,
  listDocuments,
  uploadDocument,
  deleteDocument,
  type VectorStoreStats,
  type DocumentInfo,
  type SearchResult
} from '../services/vectorStoreService';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Database,
  FileText,
  Upload,
  Trash2,
  Search,
  RefreshCw,
  HardDrive,
  AlertCircle
} from 'lucide-react';

const VectorStore: React.FC = () => {
  const [stats, setStats] = useState<VectorStoreStats | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);

  const fetchStats = async () => {
    try {
      const data = await getVectorStoreStats();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
      setError('Failed to load vector store statistics');
    }
  };

  const fetchDocuments = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
      setError('Failed to load documents');
    }
  };

  const loadData = async () => {
    setLoading(true);
    await Promise.all([fetchStats(), fetchDocuments()]);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    try {
      const data = await searchVectorStore(searchQuery, 10, 0.5);
      setSearchResults(data.results);
    } catch (err) {
      console.error('Search failed:', err);
      alert('Search failed. Please try again.');
      setSearchResults([]);
    }
  };

  const handleClearStore = async () => {
    if (!confirm('Are you sure you want to clear all documents from the vector store?')) {
      return;
    }

    try {
      await clearVectorStore();
      await loadData();
      setSearchResults([]);
      alert('Vector store cleared successfully');
    } catch (err) {
      console.error('Failed to clear store:', err);
      alert('Failed to clear vector store');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!['.txt', '.md'].some(ext => file.name.endsWith(ext))) {
      alert('Only .txt and .md files are supported');
      return;
    }

    setUploadingFile(true);
    try {
      await uploadDocument(file);
      await loadData();
      alert(`Document "${file.name}" uploaded successfully`);
      event.target.value = ''; // Reset file input
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Failed to upload document');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleDeleteDocument = async (filename: string) => {
    if (!confirm(`Delete "${filename}"?`)) return;

    try {
      await deleteDocument(filename);
      await fetchDocuments();
      alert('Document deleted successfully');
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete document');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Vector Store Monitor</h1>
          <p className="text-gray-600 mt-1">ChromaDB Status and Document Management</p>
        </div>
        <Button onClick={loadData} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg flex items-center">
          <AlertCircle className="h-5 w-5 mr-2" />
          {error}
        </div>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Documents</p>
              <p className="text-3xl font-bold mt-1">{stats?.total_documents || 0}</p>
            </div>
            <Database className="h-10 w-10 text-blue-500" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unique Sources</p>
              <p className="text-3xl font-bold mt-1">{stats?.unique_sources || 0}</p>
            </div>
            <FileText className="h-10 w-10 text-green-500" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Storage Size</p>
              <p className="text-3xl font-bold mt-1">
                {stats?.storage_size_mb?.toFixed(2) || 0}
                <span className="text-lg text-gray-600 ml-1">MB</span>
              </p>
            </div>
            <HardDrive className="h-10 w-10 text-purple-500" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Embedding Dims</p>
              <p className="text-3xl font-bold mt-1">{stats?.embedding_dimensions || 0}</p>
            </div>
            <Database className="h-10 w-10 text-orange-500" />
          </div>
        </Card>
      </div>

      {/* Configuration Info */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Collection Name</p>
            <p className="font-mono text-sm mt-1">{stats?.collection_name || 'N/A'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Embedding Model</p>
            <p className="font-mono text-sm mt-1">{stats?.embedding_model || 'N/A'}</p>
          </div>
          <div className="md:col-span-2">
            <p className="text-sm text-gray-600">Persist Directory</p>
            <p className="font-mono text-sm mt-1">{stats?.persist_directory || 'N/A'}</p>
          </div>
        </div>
      </Card>

      {/* Search Interface */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Search Documents</h2>
        <div className="flex gap-2 mb-4">
          <Input
            placeholder="Enter search query..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1"
          />
          <Button onClick={handleSearch}>
            <Search className="h-4 w-4 mr-2" />
            Search
          </Button>
        </div>

        {searchResults.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Found {searchResults.length} results</p>
            {searchResults.map((result, index) => (
              <div key={result.id} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex items-start justify-between mb-2">
                  <div className="text-sm font-medium">
                    Document {index + 1}
                    <span className="ml-2 text-gray-600">
                      (Similarity: {(result.similarity * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {result.metadata.source || 'Unknown source'}
                  </div>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-4">
                  {result.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Document Management */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Documents ({documents?.length || 0})</h2>
          <div className="flex gap-2">
            <label htmlFor="file-upload">
              <Button disabled={uploadingFile} asChild>
                <span>
                  <Upload className="h-4 w-4 mr-2" />
                  {uploadingFile ? 'Uploading...' : 'Upload Document'}
                </span>
              </Button>
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".txt,.md"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button onClick={handleClearStore} variant="destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              Clear All
            </Button>
          </div>
        </div>

        {!documents || documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No documents uploaded yet</p>
            <p className="text-sm mt-1">Upload .txt or .md files to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.path}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="font-medium">{doc.filename}</p>
                    <p className="text-xs text-gray-500">
                      {formatBytes(doc.size_bytes)} • Modified{' '}
                      {new Date(doc.modified_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => handleDeleteDocument(doc.filename)}
                  variant="ghost"
                  size="sm"
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Sources List */}
      {stats && stats.sources && stats.sources.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Document Sources</h2>
          <div className="flex flex-wrap gap-2">
            {stats.sources.map((source, index) => (
              <div
                key={index}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-mono"
              >
                {source.split('/').pop()}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default VectorStore;
