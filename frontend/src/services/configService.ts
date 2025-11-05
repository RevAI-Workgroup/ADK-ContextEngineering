/**
 * Configuration Service
 *
 * Handles API calls for context engineering configuration management
 */

import { api } from './api'
import { ContextEngineeringConfig, ConfigValidationResponse, ConfigPresetsResponse, createDefaultConfig } from '../types/config.types'

/**
 * Normalize configuration to ensure backward compatibility
 * Handles migration from old 'rag' to 'naive_rag' structure
 */
function normalizeConfig(config: any): ContextEngineeringConfig {
  const defaultConfig = createDefaultConfig()

  // Handle old 'rag' structure
  if (config.rag && !config.naive_rag) {
    config = {
      ...config,
      naive_rag: config.rag,
      rag_tool: defaultConfig.rag_tool,
    }
    delete config.rag
  }

  // Ensure all required fields exist
  return {
    ...defaultConfig,
    ...config,
    naive_rag: config.naive_rag || defaultConfig.naive_rag,
    rag_tool: config.rag_tool || defaultConfig.rag_tool,
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

