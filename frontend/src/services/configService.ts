/**
 * Configuration Service
 *
 * Handles API calls for context engineering configuration management
 */

import { api } from './api'
import { ContextEngineeringConfig, ConfigValidationResponse, ConfigPresetsResponse, createDefaultConfig, NaiveRAGConfig } from '../types/config.types'

/**
 * Checks whether a value conforms to the NaiveRAGConfig shape.
 *
 * Validates that `value` is an object containing the following properties:
 * boolean `enabled`, number `chunk_size`, number `chunk_overlap`, number `top_k`,
 * number `similarity_threshold`, and string `embedding_model`.
 *
 * @returns `true` if `value` has the required NaiveRAGConfig properties, `false` otherwise.
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
 * Normalize a ContextEngineeringConfig and migrate legacy `rag` entries into the `naive_rag` shape.
 *
 * @param config - Partial configuration to normalize; may contain a legacy `rag` property that will be migrated if valid
 * @returns A complete ContextEngineeringConfig with defaults applied and `naive_rag`/`rag_tool` ensured (legacy `rag` migrated or replaced by defaults)
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
