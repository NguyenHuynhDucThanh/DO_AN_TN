import { apiClient } from '../../api/client'
import type { Schedule, Slot } from '../../types/domain'

export const scheduleKeys = {
  all: ['schedules'] as const,
  byDoctor: (doctorId: string) => ['schedules', 'doctor', doctorId] as const,
  available: (filters: object) => ['slots', 'available', filters] as const,
}
export async function listSchedules(doctorId?: string) {
  const { data } = await apiClient.get<Schedule[]>('/schedules', { params: { doctor_id: doctorId || undefined } })
  return data
}
export async function listAvailableSlots(filters: { from_at: string; to_at: string; doctor_id?: string; specialty_id?: string }) {
  const { data } = await apiClient.get<Slot[]>('/schedules/available-slots', { params: filters })
  return data
}
