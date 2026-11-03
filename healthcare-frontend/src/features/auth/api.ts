import { apiClient } from '../../api/client'
import type { AuthUser, LoginInput, RegisterInput } from './types'

type SessionResponse = { user: AuthUser }

export async function login(input: LoginInput) {
  const response = await apiClient.post<SessionResponse>('/auth/login', input)
  return response.data.user
}

export async function register(input: RegisterInput) {
  const response = await apiClient.post<SessionResponse>('/auth/register', input)
  return response.data.user
}

export async function getCurrentUser() {
  const response = await apiClient.get<AuthUser>('/auth/me')
  return response.data
}

export async function logout() {
  await apiClient.post('/auth/logout')
}
