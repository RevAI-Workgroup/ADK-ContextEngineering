/**
 * Vector Store API Service
 *
 * Handles all vector store and document management API calls
 */

import { api } from './api';

export interface VectorStoreStats {
  total_documents: number;
  unique_sources: number;
  sources: string[];
  collection_name: string;
  persist_directory: string;
  storage_size_mb: number;
  embedding_model: string;
  embedding_dimensions: number;
  timestamp?: string;
}

export interface DocumentInfo {
  filename: string;
  path: string;
  size_bytes: number;
  modified_at: string;
}

export interface SearchResult {
  id: string;
  text: string;
  metadata: Record<string, any>;
  similarity: number;
}

export interface UploadResponse {
  success: boolean;
  filename: string;
  file_size_bytes: number;
  chunks_created: number;
  doc_id: string;
  timestamp: string;
}

/**
 * Get vector store statistics
 */
export const getVectorStoreStats = async (): Promise<VectorStoreStats> => {
  const response = await api.get('/api/vector-store/stats');
  return response.data;
};

/**
 * Search the vector store
 */
export const searchVectorStore = async (
  query: string,
  topK: number = 5,
  similarityThreshold: number = 0.7
): Promise<{ results: SearchResult[]; count: number; query: string }> => {
  const response = await api.get('/api/vector-store/search', {
    params: {
      query,
      top_k: topK,
      similarity_threshold: similarityThreshold
    }
  });
  return response.data;
};

/**
 * Clear the vector store
 */
export const clearVectorStore = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/vector-store/clear');
  return response.data;
};

/**
 * List all documents in knowledge base
 */
export const listDocuments = async (): Promise<{ documents: DocumentInfo[]; count: number }> => {
  const response = await api.get('/api/documents');
  return response.data;
};

/**
 * Upload a document
 */
export const uploadDocument = async (
  file: File,
  description?: string
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  if (description) {
    formData.append('description', description);
  }

  // Don't set Content-Type header manually for FormData
  // The browser will set it automatically with the correct boundary
  const response = await api.post('/api/documents/upload', formData);
  return response.data;
};

/**
 * Delete a document
 */
export const deleteDocument = async (filename: string): Promise<{ success: boolean; message: string }> => {
  const response = await api.delete(`/api/documents/${filename}`);
  return response.data;
};

/**
 * Bulk ingest documents from directory
 */
export const ingestDocuments = async (
  directory: string,
  recursive: boolean = true,
  fileExtensions?: string[]
): Promise<{ success: boolean; documents_processed: number; total_chunks: number }> => {
  const response = await api.post('/api/documents/ingest', {
    directory,
    recursive,
    file_extensions: fileExtensions
  });
  return response.data;
};
