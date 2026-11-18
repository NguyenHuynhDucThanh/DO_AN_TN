import { apiClient } from '../../api/client'
import type { AvailableSlot, Schedule, Slot } from '../../types/domain'

export const scheduleKeys = {
  all: ['schedules'] as const,
  byDoctor: (doctorId: string) => ['schedules', 'doctor', doctorId] as const,
  slots: (scheduleId: string) => ['schedules', scheduleId, 'slots'] as const,
  available: (filters: object) => ['slots', 'available', filters] as const,
}
export async function listSchedules(doctorId?: string) {
  const { data } = await apiClient.get<Schedule[]>('/schedules', { params: { doctor_id: doctorId || undefined } })
  return data
}
export async function listAvailableSlots(filters: { from_at: string; to_at: string; doctor_id?: string; specialty_id?: string; limit?: number }) {
  const { data } = await apiClient.get<AvailableSlot[]>('/schedules/available-slots', { params: filters })
  return data
}
export async function listScheduleSlots(scheduleId: string) {
  const { data } = await apiClient.get<Slot[]>(`/schedules/${scheduleId}/slots`)
  return data
}
export async function createSchedule(payload: { doctor_id: string; start_at: string; end_at: string; slot_duration_minutes: number }) {
  const { data } = await apiClient.post<Schedule>('/schedules', payload)
  return data
}
export async function updateSchedule(id: string, payload: { start_at?: string; end_at?: string; slot_duration_minutes?: number; status?: Schedule['status'] }) {
  const { data } = await apiClient.patch<Schedule>(`/schedules/${id}`, payload)
  return data
}
export async function generateSlots(scheduleId: string) {
  const { data } = await apiClient.post<Slot[]>(`/schedules/${scheduleId}/slots/generate`)
  return data
}
export async function setSlotStatus(slotId: string, blocked: boolean) {
  const { data } = await apiClient.patch<Slot>(`/schedules/slots/${slotId}/status`, { blocked })
  return data
}
