import { apiClient } from '../../api/client'
import type { Doctor } from '../../types/domain'

export const doctorKeys = { all: ['doctors'] as const, detail: (id: string) => ['doctors', id] as const }
export async function listDoctors(specialtyId?: string, active?: boolean) {
  const { data } = await apiClient.get<Doctor[]>('/doctors', { params: { specialty_id: specialtyId || undefined, active } })
  return data
}
export async function getDoctor(id: string) {
  const { data } = await apiClient.get<Doctor>(`/doctors/${id}`)
  return data
}
export async function createDoctor(payload: { user_id: string; specialty_id: string; license_number: string; biography?: string }) {
  const { data } = await apiClient.post<Doctor>('/doctors', payload)
  return data
}
export async function updateDoctor(id: string, payload: { specialty_id?: string; license_number?: string; biography?: string; is_active?: boolean }) {
  const { data } = await apiClient.patch<Doctor>(`/doctors/${id}`, payload)
  return data
}
