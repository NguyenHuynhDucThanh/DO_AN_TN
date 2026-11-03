export interface HealthResponse {
  status: 'ok' | 'unavailable'
  application: string
  environment: string
}
