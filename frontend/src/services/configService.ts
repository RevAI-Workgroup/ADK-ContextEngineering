/**
 * Configuration Service
 * 
 * Handles API calls for context engineering configuration management
 */

import { api } from './api'
import { ContextEngineeringConfig, ConfigValidationResponse, ConfigPresetsResponse } from '../types/config.types'

export const configService = {
  /**
   * Get available configuration presets
   */
  async getPresets(): Promise<ConfigPresetsResponse> {
    const response = await api.get('/config/presets')
    return response.data
  },

  /**
   * Validate a configuration object
   */
  async validateConfig(config: ContextEngineeringConfig): Promise<ConfigValidationResponse> {
    const response = await api.post('/config/validate', config)
    return response.data
  },

  /**
   * Get the default configuration
   */
  async getDefaultConfig(): Promise<ContextEngineeringConfig> {
    const response = await api.get('/config/default')
    return response.data
  },
}

