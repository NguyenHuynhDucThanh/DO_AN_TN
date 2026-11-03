import { apiClient } from '../../api/client'
import type { Specialty } from '../../types/domain'

export const specialtyKeys = { all: ['specialties'] as const, detail: (id: string) => ['specialties', id] as const }

export async function listSpecialties(active?: boolean) {
  const { data } = await apiClient.get<Specialty[]>('/specialties', { params: active === undefined ? {} : { active } })
  return data
}
export async function getSpecialty(id: string) {
  const { data } = await apiClient.get<Specialty>(`/specialties/${id}`)
  return data
}
export async function createSpecialty(payload: { code: string; name: string; description?: string }) {
  const { data } = await apiClient.post<Specialty>('/specialties', payload)
  return data
}
export async function updateSpecialty(id: string, payload: { name?: string; description?: string }) {
  const { data } = await apiClient.patch<Specialty>(`/specialties/${id}`, payload)
  return data
}
export async function setSpecialtyStatus(id: string, is_active: boolean) {
  const { data } = await apiClient.patch<Specialty>(`/specialties/${id}/status`, { is_active })
  return data
}
