import { apiClient, websocketUrl } from '../../api/client'
import type { Handoff } from '../../types/domain'

export const handoffKeys = { all: ['handoffs'] as const }
export async function listHandoffs() {
  const { data } = await apiClient.get<Handoff[]>('/handoffs')
  return data
}
export async function createHandoff(payload: { reason: string; priority: Handoff['priority']; source?: string }) {
  const { data } = await apiClient.post<Handoff>('/handoffs', payload)
  return data
}
export async function updateHandoff(id: string, payload: { status: Handoff['status']; assigned_to?: string }) {
  const { data } = await apiClient.patch<Handoff>(`/handoffs/${id}`, payload)
  return data
}

export function handoffWebSocketUrl() {
  return websocketUrl('/handoffs/ws')
}
