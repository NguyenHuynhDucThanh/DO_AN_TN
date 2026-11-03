import { apiClient } from '../../api/client'
import type { MedicalRecord } from '../../types/domain'

export type MedicalRecordPayload = {
  appointment_id?: string
  symptoms: string
  clinical_notes: string
  doctor_conclusion: string
  follow_up_instructions: string
}
export const medicalRecordKeys = {
  history: ['medical-records', 'history'] as const,
  detail: (id: string) => ['medical-records', id] as const,
  appointment: (id: string) => ['medical-records', 'appointment', id] as const,
}
export async function listMedicalHistory() {
  const { data } = await apiClient.get<MedicalRecord[]>('/medical-records/me/history')
  return data
}
export async function getMedicalRecord(id: string) {
  const { data } = await apiClient.get<MedicalRecord>(`/medical-records/${id}`)
  return data
}
export async function getMedicalRecordByAppointment(id: string) {
  const { data } = await apiClient.get<MedicalRecord>(`/medical-records/by-appointment/${id}`)
  return data
}
export async function createMedicalRecord(payload: MedicalRecordPayload & { appointment_id: string }) {
  const { data } = await apiClient.post<MedicalRecord>('/medical-records', payload)
  return data
}
export async function updateMedicalRecord(id: string, payload: Omit<MedicalRecordPayload, 'appointment_id'>) {
  const { data } = await apiClient.patch<MedicalRecord>(`/medical-records/${id}`, payload)
  return data
}
