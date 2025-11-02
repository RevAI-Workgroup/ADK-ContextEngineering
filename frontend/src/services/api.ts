import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
})

// Add request interceptor for Content-Type and logging
api.interceptors.request.use(
  (config) => {
    // Only set Content-Type to application/json if data is not FormData
    // This allows the browser to set multipart/form-data with boundaries automatically
    if (config.data && !(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json'
    }
    
    console.log('[API Request]', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for logging and error handling
api.interceptors.response.use(
  (response) => {
    console.log('[API Response]', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('[API Response Error]', error.response?.status, error.config?.url)
    return Promise.reject(error)
  }
)

