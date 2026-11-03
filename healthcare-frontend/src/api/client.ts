import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

export const DEV_ACTOR_STORAGE_KEY = 'healthcare.devActor'
export const AUTH_SESSION_EXPIRED_EVENT = 'healthcare:session-expired'
export const DEV_ACTOR_CHANGED_EVENT = 'healthcare:dev-actor-changed'
export const DEV_AUTH_ENABLED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_AUTH === 'true'
const CSRF_COOKIE_NAME = 'healthcare_csrf'

const baseURL = import.meta.env.VITE_API_BASE_URL?.trim() || (import.meta.env.MODE === 'test' ? 'http://test/api/v1' : '')
if (!baseURL) {
  throw new Error('Thiếu VITE_API_BASE_URL. Hãy tạo .env từ .env.example và khởi động lại Vite.')
}

export const apiClient = axios.create({
  baseURL,
  timeout: 10_000,
  headers: { Accept: 'application/json' },
})

export function websocketUrl(path: string) {
  const url = new URL(`${baseURL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

function readCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`
  const value = document.cookie.split('; ').find((cookie) => cookie.startsWith(prefix))
  return value ? decodeURIComponent(value.slice(prefix.length)) : null
}

function isStateChanging(method?: string) {
  return ['post', 'put', 'patch', 'delete'].includes(method?.toLowerCase() ?? '')
}

apiClient.interceptors.request.use((config) => {
  if (isStateChanging(config.method)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME)
    if (csrfToken) config.headers.set('X-CSRF-Token', csrfToken)
  }
  if (DEV_AUTH_ENABLED) {
    const rawActor = window.localStorage.getItem(DEV_ACTOR_STORAGE_KEY)
    if (rawActor) {
      try {
        const actor = JSON.parse(rawActor) as { userId?: string }
        if (actor.userId) config.headers.set('X-Dev-User-Id', actor.userId)
      } catch {
        window.localStorage.removeItem(DEV_ACTOR_STORAGE_KEY)
      }
    }
  }
  return config
})

apiClient.defaults.withCredentials = true

type RetryableConfig = InternalAxiosRequestConfig & { _authRetry?: boolean }
let refreshPromise: Promise<unknown> | null = null

function isAuthBootstrapRequest(url?: string) {
  return ['/auth/login', '/auth/register', '/auth/refresh'].some((path) => url?.endsWith(path))
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined
    if (error.response?.status !== 401 || !config || config._authRetry || isAuthBootstrapRequest(config.url)) {
      return Promise.reject(error)
    }
    if (!readCookie(CSRF_COOKIE_NAME)) {
      window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT))
      return Promise.reject(error)
    }
    config._authRetry = true
    try {
      refreshPromise ??= apiClient.post('/auth/refresh').finally(() => {
        refreshPromise = null
      })
      await refreshPromise
      config.headers.delete('X-CSRF-Token')
      return apiClient.request(config)
    } catch {
      window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT))
      return Promise.reject(error)
    }
  },
)
