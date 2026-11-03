export type Role = 'PATIENT' | 'DOCTOR' | 'STAFF' | 'ADMIN'

export type Specialty = {
  id: string
  code: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type Doctor = {
  id: string
  user_id: string
  specialty_id: string
  license_number: string
  biography: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  user: { id: string; full_name: string; email: string; phone: string | null }
  specialty: { id: string; code: string; name: string }
}

export type Schedule = {
  id: string
  doctor_id: string
  start_at: string
  end_at: string
  slot_duration_minutes: number
  status: 'ACTIVE' | 'CANCELLED'
  created_at: string
  updated_at: string
}

export type Slot = {
  id: string
  schedule_id: string
  start_at: string
  end_at: string
  status: 'AVAILABLE' | 'BOOKED' | 'BLOCKED'
  created_at: string
  updated_at: string
}

export type AppointmentStatus = 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW'

export type Appointment = {
  id: string
  patient_id: string
  schedule_slot_id: string
  status: AppointmentStatus
  booked_at: string
  cancelled_at: string | null
  cancelled_by: string | null
  cancellation_reason: string | null
  completed_at: string | null
  no_show_at: string | null
  created_at: string
  updated_at: string
}

export type MedicalRecord = {
  id: string
  appointment_id: string
  symptoms: string
  clinical_notes: string
  doctor_conclusion: string
  follow_up_instructions: string
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
}

export type DocumentMetadata = {
  id: string
  title: string
  file_name: string
  file_type: 'CSV' | 'PDF' | 'DOCX'
  storage_key: string
  source_name: string | null
  source_url: string | null
  checksum_sha256: string
  version_number: number
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED'
  ingestion_status: 'NOT_INGESTED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  uploaded_by: string
  approved_by: string | null
  approved_at: string | null
  ingestion_error: string | null
  created_at: string
  updated_at: string
}

export type Handoff = {
  id: string
  requester_id: string
  assigned_to: string | null
  source: string
  reason: string
  priority: 'NORMAL' | 'HIGH' | 'URGENT'
  status: 'PENDING' | 'IN_PROGRESS' | 'RESOLVED'
  resolved_at: string | null
  created_at: string
  updated_at: string
}
