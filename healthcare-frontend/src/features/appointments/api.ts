import { apiClient } from '../../api/client'
import type { Appointment, AppointmentStatus } from '../../types/domain'

export const appointmentKeys = { all: ['appointments'] as const, detail: (id: string) => ['appointments', id] as const }
export async function listAppointments() {
  const { data } = await apiClient.get<Appointment[]>('/appointments')
  return data
}
export async function createAppointment(scheduleSlotId: string) {
  const { data } = await apiClient.post<Appointment>('/appointments', { schedule_slot_id: scheduleSlotId })
  return data
}
export async function cancelAppointment(id: string, reason: string) {
  const { data } = await apiClient.post<Appointment>(`/appointments/${id}/cancel`, { reason })
  return data
}
export async function setAppointmentOutcome(id: string, status: Extract<AppointmentStatus, 'COMPLETED' | 'NO_SHOW'>) {
  const { data } = await apiClient.post<Appointment>(`/appointments/${id}/outcome`, { status })
  return data
}
