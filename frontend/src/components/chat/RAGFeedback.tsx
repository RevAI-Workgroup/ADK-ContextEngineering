import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { ChevronDown, ChevronRight, Database, FileText, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { RAGMetadata } from '../../types/message.types'
import { cn } from '@/lib/utils'

interface RAGFeedbackProps {
  metadata: RAGMetadata
}

export function RAGFeedback({ metadata }: RAGFeedbackProps) {
  // Start expanded by default to show RAG information
  const [isExpanded, setIsExpanded] = useState(true)

  // Check which RAG method was used (presence checks only)
  const hasNaiveRAG = metadata?.rag_status !== undefined
  const hasRAGTool = metadata?.rag_tool_status !== undefined

  if (!hasNaiveRAG && !hasRAGTool) {
    return null
  }

  // Debug: log what we received
  console.log('[RAGFeedback] metadata:', metadata)

  // Check if each RAG type actually retrieved documents
  const hasNaiveRAGWithDocs = hasNaiveRAG && (
    (metadata.rag_documents && metadata.rag_documents.length > 0) ||
    (metadata.rag_retrieved_docs && metadata.rag_retrieved_docs > 0)
  )
  const hasRAGToolWithDocs = hasRAGTool && (
    (metadata.rag_tool_documents && metadata.rag_tool_documents.length > 0) ||
    (metadata.rag_tool_calls && metadata.rag_tool_calls > 0)
  )

  // Determine which RAG method to display based on actual results
  // Prioritize showing whichever one actually returned documents
  // If both have docs, prefer RAG-as-tool; if neither, show whichever has a status
  const displayRAGTool = hasRAGToolWithDocs || (hasRAGTool && !hasNaiveRAGWithDocs)
  const displayNaiveRAG = hasNaiveRAGWithDocs || (hasNaiveRAG && !hasRAGToolWithDocs)

  // Destructure all fields
  const { rag_status, rag_retrieved_docs, rag_sources, rag_avg_similarity, rag_error, rag_message, rag_documents } = metadata
  const { rag_tool_status, rag_tool_name, rag_tool_calls, rag_tool_documents } = metadata

  // Get the active status and related fields based on which RAG type we're displaying
  const activeStatus = displayRAGTool ? rag_tool_status : rag_status
  const activeDocuments = displayRAGTool ? rag_tool_documents : rag_documents
  const activeRetrievedCount = displayRAGTool ? rag_tool_calls : rag_retrieved_docs
  const activeError = displayRAGTool ? undefined : rag_error // RAG-as-tool errors may be in status
  const activeMessage = displayRAGTool ? undefined : rag_message // RAG-as-tool messages may be in status

  // Normalize status: map 'registered' to 'success' for RAG-as-tool, otherwise use as-is
  const normalizeStatus = (status: string | undefined): string | undefined => {
    if (status === undefined) {
      return undefined
    }
    // Map tool statuses to equivalent naive RAG statuses
    if (status === 'registered') {
      return 'success' // registered is equivalent to success
    }
    // If status matches known statuses, use as-is
    if (['success', 'empty', 'error'].includes(status)) {
      return status
    }
    // Unknown status defaults to undefined (will use default case)
    return status
  }

  const normalizedStatus = normalizeStatus(activeStatus)

  // Determine status icon and color using normalized status
  const getStatusConfig = () => {
    switch (normalizedStatus) {
      case 'success':
        return {
          icon: <CheckCircle className="h-4 w-4" />,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200'
        }
      case 'empty':
        return {
          icon: <AlertCircle className="h-4 w-4" />,
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200'
        }
      case 'error':
        return {
          icon: <XCircle className="h-4 w-4" />,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200'
        }
      default:
        return {
          icon: <Database className="h-4 w-4" />,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200'
        }
    }
  }

  const statusConfig = getStatusConfig()

  return (
    <Card className={cn('border', statusConfig.borderColor, statusConfig.bgColor)}>
      <CardHeader
        className="p-3 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isExpanded ? <ChevronDown className="h-4 w-4 text-gray-700" /> : <ChevronRight className="h-4 w-4 text-gray-700" />}
            <div className={cn('flex items-center gap-2', statusConfig.color)}>
              {statusConfig.icon}
              <CardTitle className="text-sm font-medium">
                {displayRAGTool ? 'RAG-as-tool' : 'Naive RAG'} Retrieval
                {displayRAGTool && rag_tool_name && (
                  <span className="ml-2 text-xs font-normal text-gray-600">({rag_tool_name})</span>
                )}
              </CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Show method badge */}
            {displayRAGTool && (
              <Badge variant="outline" className="text-xs bg-purple-50 border-purple-200 text-purple-700">
                Tool
              </Badge>
            )}
            {displayNaiveRAG && (
              <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200 text-blue-700">
                Naive
              </Badge>
            )}

            {normalizedStatus === 'success' && (
              <>
                {activeRetrievedCount !== undefined && (
                  <Badge variant="secondary" className="text-xs bg-white">
                    {activeRetrievedCount} {displayRAGTool ? 'calls' : 'docs'}
                  </Badge>
                )}
                {rag_avg_similarity !== undefined && displayNaiveRAG && (
                  <Badge variant="outline" className="text-xs bg-white">
                    {(rag_avg_similarity * 100).toFixed(1)}% similarity
                  </Badge>
                )}
              </>
            )}
            <Badge
              variant={normalizedStatus === 'success' ? 'default' : 'secondary'}
              className="text-xs"
            >
              {activeStatus ?? 'unknown'}
            </Badge>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-3 pt-0 space-y-3">
          {/* Success State */}
          {normalizedStatus === 'success' && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <Database className="h-4 w-4 text-gray-700" />
                <span className="font-medium text-gray-900">
                  {displayRAGTool 
                    ? `${activeRetrievedCount ?? 0} tool call${(activeRetrievedCount ?? 0) !== 1 ? 's' : ''} made`
                    : `${activeRetrievedCount ?? 0} document${(activeRetrievedCount ?? 0) !== 1 ? 's' : ''} retrieved`
                  }
                </span>
              </div>

              {rag_avg_similarity !== undefined && displayNaiveRAG && (
                <div className="text-sm text-gray-700">
                  Average similarity: <span className="font-mono text-gray-900">{(rag_avg_similarity * 100).toFixed(2)}%</span>
                </div>
              )}

              {/* Retrieved Documents - works for both RAG types */}
              {activeDocuments && activeDocuments.length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-900">Retrieved Documents:</div>
                  {activeDocuments.map((doc, idx) => (
                    <div key={idx} className="bg-white p-3 rounded border border-green-200">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-green-600" />
                          <span className="text-xs font-medium text-gray-900">
                            Document {idx + 1}
                          </span>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {(doc.similarity * 100).toFixed(1)}% match
                        </Badge>
                      </div>

                      <div className="text-xs text-gray-600 mb-2">
                        <span className="font-mono">{doc.source.split('/').pop()}</span>
                        {doc.chunk_index !== undefined && doc.chunk_index !== '' && (
                          <span className="ml-2">(chunk {doc.chunk_index})</span>
                        )}
                      </div>

                      <div className="text-sm text-gray-800 bg-gray-50 p-2 rounded border border-gray-200 max-h-48 overflow-y-auto">
                        <pre className="whitespace-pre-wrap font-sans">{doc.text}</pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Sources Summary - only for naive RAG */}
              {rag_sources && rag_sources.length > 0 && displayNaiveRAG && (
                <div className="mt-2">
                  <div className="text-sm font-medium mb-1 text-gray-900">Sources:</div>
                  <div className="flex flex-wrap gap-1">
                    {rag_sources.map((source, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs flex items-center gap-1 bg-white">
                        <FileText className="h-3 w-3" />
                        {source.split('/').pop()}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Empty State - explicitly handle both RAG types */}
          {normalizedStatus === 'empty' && (
            <div className="text-sm text-gray-700">
              {displayRAGTool 
                ? (activeMessage || 'No documents found via RAG-as-tool')
                : (activeMessage || 'No documents found in vector store')
              }
            </div>
          )}

          {/* Error State - explicitly handle both RAG types */}
          {normalizedStatus === 'error' && (
            <div className="text-sm text-red-700 bg-red-50 p-2 rounded">
              {displayRAGTool
                ? (activeError || `RAG-as-tool error: ${activeStatus}`)
                : (activeError || 'An error occurred during retrieval')
              }
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}
