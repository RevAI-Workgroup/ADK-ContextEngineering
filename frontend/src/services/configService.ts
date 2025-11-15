/**
 * Configuration Service
 *
 * Handles API calls for context engineering configuration management
 */

import { api } from './api'
import { ContextEngineeringConfig, ConfigValidationResponse, ConfigPresetsResponse, createDefaultConfig, NaiveRAGConfig } from '../types/config.types'

/**
 * Type guard to validate if an object matches NaiveRAGConfig structure
 */
function isValidNaiveRAGConfig(value: unknown): value is NaiveRAGConfig {
  if (!value || typeof value !== 'object') {
    return false
  }

  const obj = value as Record<string, unknown>

  return (
    typeof obj.enabled === 'boolean' &&
    typeof obj.chunk_size === 'number' &&
    typeof obj.chunk_overlap === 'number' &&
    typeof obj.top_k === 'number' &&
    typeof obj.similarity_threshold === 'number' &&
    typeof obj.embedding_model === 'string'
  )
}

/**
 * Normalize configuration to ensure backward compatibility
 * Handles migration from old 'rag' to 'naive_rag' structure
 */
function normalizeConfig(config: Partial<ContextEngineeringConfig> & { rag?: unknown }): ContextEngineeringConfig {
  const defaultConfig = createDefaultConfig()

  // Create a copy to avoid mutating the input
  const migratedConfig = { ...config }

  // Handle old 'rag' structure
  if (migratedConfig.rag && !migratedConfig.naive_rag) {
    if (isValidNaiveRAGConfig(migratedConfig.rag)) {
      migratedConfig.naive_rag = migratedConfig.rag
      migratedConfig.rag_tool = defaultConfig.rag_tool
      delete migratedConfig.rag
    } else {
      console.warn(
        'Invalid RAG config structure detected during migration. Expected NaiveRAGConfig shape but got:',
        migratedConfig.rag,
        'Falling back to default naive_rag configuration.'
      )
      migratedConfig.naive_rag = defaultConfig.naive_rag
      migratedConfig.rag_tool = defaultConfig.rag_tool
      delete migratedConfig.rag
    }
  }

  // Ensure all required fields exist
  return {
    ...defaultConfig,
    ...migratedConfig,
    naive_rag: migratedConfig.naive_rag ?? defaultConfig.naive_rag,
    rag_tool: migratedConfig.rag_tool ?? defaultConfig.rag_tool,
  }
}

export const configService = {
  /**
   * Get available configuration presets
   */
  async getPresets(): Promise<ConfigPresetsResponse> {
    const response = await api.get('/api/config/presets')
    const data = response.data

    // Normalize all presets
    if (data.presets) {
      Object.keys(data.presets).forEach(key => {
        data.presets[key] = normalizeConfig(data.presets[key])
      })
    }

    return data
  },

  /**
   * Validate a configuration object
   */
  async validateConfig(config: ContextEngineeringConfig): Promise<ConfigValidationResponse> {
    const response = await api.post('/api/config/validate', { config })
    return response.data
  },

  /**
   * Get the default configuration
   */
  async getDefaultConfig(): Promise<ContextEngineeringConfig> {
    const response = await api.get('/api/config/default')
    return normalizeConfig(response.data)
  },
}

