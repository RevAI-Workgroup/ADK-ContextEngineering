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

  // Check which RAG method was used
  const hasNaiveRAG = metadata?.rag_status !== undefined
  const hasRAGTool = metadata?.rag_tool_status !== undefined

  if (!hasNaiveRAG && !hasRAGTool) {
    return null
  }

  // Debug: log what we received
  console.log('[RAGFeedback] metadata:', metadata)

  // Determine which RAG method to display (prioritize the one that has results)
  const isNaiveRAG = hasNaiveRAG && metadata.rag_status === 'success'
  const isRAGTool = hasRAGTool && metadata.rag_tool_status === 'registered'

  const { rag_status, rag_retrieved_docs, rag_sources, rag_avg_similarity, rag_error, rag_message, rag_documents } = metadata
  const { rag_tool_status, rag_tool_name, rag_tool_calls, rag_tool_documents } = metadata

  // Determine status icon and color
  const getStatusConfig = () => {
    switch (rag_status) {
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
                {isRAGTool ? 'RAG-as-tool' : 'Naive RAG'} Retrieval
              </CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Show method badge */}
            {isRAGTool && (
              <Badge variant="outline" className="text-xs bg-purple-50 border-purple-200 text-purple-700">
                Tool
              </Badge>
            )}
            {isNaiveRAG && (
              <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200 text-blue-700">
                Naive
              </Badge>
            )}

            {rag_status === 'success' && (
              <>
                <Badge variant="secondary" className="text-xs bg-white">
                  {rag_retrieved_docs} docs
                </Badge>
                {rag_avg_similarity !== undefined && (
                  <Badge variant="outline" className="text-xs bg-white">
                    {(rag_avg_similarity * 100).toFixed(1)}% similarity
                  </Badge>
                )}
              </>
            )}
            <Badge
              variant={rag_status === 'success' ? 'default' : 'secondary'}
              className="text-xs"
            >
              {rag_status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-3 pt-0 space-y-3">
          {/* Success State */}
          {rag_status === 'success' && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <Database className="h-4 w-4 text-gray-700" />
                <span className="font-medium text-gray-900">{rag_retrieved_docs} documents retrieved</span>
              </div>

              {rag_avg_similarity !== undefined && (
                <div className="text-sm text-gray-700">
                  Average similarity: <span className="font-mono text-gray-900">{(rag_avg_similarity * 100).toFixed(2)}%</span>
                </div>
              )}

              {/* Retrieved Documents */}
              {rag_documents && rag_documents.length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-900">Retrieved Documents:</div>
                  {rag_documents.map((doc, idx) => (
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

              {/* Sources Summary */}
              {rag_sources && rag_sources.length > 0 && (
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

          {/* Empty State */}
          {rag_status === 'empty' && (
            <div className="text-sm text-gray-700">
              {rag_message || 'No documents found in vector store'}
            </div>
          )}

          {/* Error State */}
          {rag_status === 'error' && (
            <div className="text-sm text-red-700 bg-red-50 p-2 rounded">
              {rag_error || 'An error occurred during retrieval'}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}
