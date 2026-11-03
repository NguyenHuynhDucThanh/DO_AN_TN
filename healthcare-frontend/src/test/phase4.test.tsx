import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { BookingPage } from '../features/appointments/BookingPage'
import { DoctorAppointmentsPage } from '../features/appointments/DoctorAppointmentsPage'
import { PatientAppointmentsPage } from '../features/appointments/PatientAppointmentsPage'
import { createAppointment, cancelAppointment, listAppointments, setAppointmentOutcome } from '../features/appointments/api'
import { DoctorListPage } from '../features/doctors/DoctorListPage'
import { listDoctors } from '../features/doctors/api'
import { DoctorMedicalRecordPage } from '../features/medical-records/DoctorMedicalRecordPage'
import { PatientMedicalHistoryPage } from '../features/medical-records/PatientMedicalHistoryPage'
import { createMedicalRecord, getMedicalRecordByAppointment, listMedicalHistory } from '../features/medical-records/api'
import { listAvailableSlots } from '../features/schedules/api'
import { SpecialtyListPage } from '../features/specialties/SpecialtyListPage'
import { listSpecialties } from '../features/specialties/api'
import type { Appointment, Doctor, MedicalRecord, Slot, Specialty } from '../types/domain'
import { renderPage } from './render'

vi.mock('../features/specialties/api', () => ({
  specialtyKeys: { all: ['specialties'], detail: (id: string) => ['specialties', id] },
  listSpecialties: vi.fn(), getSpecialty: vi.fn(), createSpecialty: vi.fn(), updateSpecialty: vi.fn(), setSpecialtyStatus: vi.fn(),
}))
vi.mock('../features/doctors/api', () => ({
  doctorKeys: { all: ['doctors'], detail: (id: string) => ['doctors', id] },
  listDoctors: vi.fn(), getDoctor: vi.fn(), createDoctor: vi.fn(), updateDoctor: vi.fn(),
}))
vi.mock('../features/schedules/api', () => ({
  scheduleKeys: { all: ['schedules'], byDoctor: (id: string) => ['schedules', id], available: (filters: object) => ['slots', filters] },
  listAvailableSlots: vi.fn(), listSchedules: vi.fn(),
}))
vi.mock('../features/appointments/api', () => ({
  appointmentKeys: { all: ['appointments'], detail: (id: string) => ['appointments', id] },
  listAppointments: vi.fn(), createAppointment: vi.fn(), cancelAppointment: vi.fn(), setAppointmentOutcome: vi.fn(),
}))
vi.mock('../features/medical-records/api', () => ({
  medicalRecordKeys: { history: ['medical-records', 'history'], detail: (id: string) => ['medical-records', id], appointment: (id: string) => ['medical-records', 'appointment', id] },
  listMedicalHistory: vi.fn(), getMedicalRecord: vi.fn(), getMedicalRecordByAppointment: vi.fn(), createMedicalRecord: vi.fn(), updateMedicalRecord: vi.fn(),
}))

const specialty: Specialty = {
  id: '11111111-1111-4111-8111-111111111111', code: 'DA_LIEU', name: 'Da liễu', description: 'Khám da', is_active: true,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
}
const doctor: Doctor = {
  id: '22222222-2222-4222-8222-222222222222', user_id: '33333333-3333-4333-8333-333333333333', specialty_id: specialty.id,
  license_number: 'DEMO-01', biography: 'Bác sĩ demo', is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
  user: { id: '33333333-3333-4333-8333-333333333333', full_name: 'BS. Minh An', email: 'doctor@example.invalid', phone: null },
  specialty: { id: specialty.id, code: specialty.code, name: specialty.name },
}
const slot: Slot = {
  id: '44444444-4444-4444-8444-444444444444', schedule_id: '55555555-5555-4555-8555-555555555555',
  start_at: '2030-01-15T01:00:00Z', end_at: '2030-01-15T01:30:00Z', status: 'AVAILABLE', created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
}
const appointment: Appointment = {
  id: '66666666-6666-4666-8666-666666666666', patient_id: '77777777-7777-4777-8777-777777777777', schedule_slot_id: slot.id,
  status: 'CONFIRMED', booked_at: '2026-10-20T01:00:00Z', cancelled_at: null, cancelled_by: null, cancellation_reason: null,
  completed_at: null, no_show_at: null, created_at: '2026-10-20T01:00:00Z', updated_at: '2026-10-20T01:00:00Z',
}
const medicalRecord: MedicalRecord = {
  id: '88888888-8888-4888-8888-888888888888', appointment_id: appointment.id,
  symptoms: 'Mệt nhẹ', clinical_notes: 'Ghi chú demo', doctor_conclusion: 'Theo dõi sức khỏe', follow_up_instructions: 'Tái khám khi cần',
  created_by: doctor.user_id, updated_by: doctor.user_id, created_at: '2026-10-20T01:00:00Z', updated_at: '2026-10-20T02:00:00Z',
}

function axiosError(status: number, detail: string) {
  return Object.assign(new Error(detail), { isAxiosError: true, response: { status, data: { error: { code: 'test_error', detail } } } })
}

beforeEach(() => {
  window.localStorage.clear()
  vi.mocked(listSpecialties).mockResolvedValue([specialty])
  vi.mocked(listDoctors).mockResolvedValue([doctor])
  vi.mocked(listAvailableSlots).mockResolvedValue([slot])
  vi.mocked(listAppointments).mockResolvedValue([appointment])
  vi.mocked(listMedicalHistory).mockResolvedValue([medicalRecord])
})

describe('Phase 4 frontend core', () => {
  it('renders the specialty list', async () => {
    renderPage(<SpecialtyListPage />)
    expect(await screen.findByText('Da liễu')).toBeInTheDocument()
    expect(screen.getByText('Khám da')).toBeInTheDocument()
  })

  it('filters doctors by specialty', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorListPage />)
    await screen.findByText('BS. Minh An')
    await user.click(screen.getByRole('combobox'))
    await user.click(await screen.findByRole('option', { name: 'Da liễu' }))
    await waitFor(() => expect(listDoctors).toHaveBeenLastCalledWith(specialty.id, true))
  })

  it('shows available slots', async () => {
    renderPage(<BookingPage />)
    expect(await screen.findByRole('button', { name: 'Chọn khung giờ' })).toBeInTheDocument()
    expect(listAvailableSlots).toHaveBeenCalled()
  })

  it('submits the booking form after explicit confirmation', async () => {
    const user = userEvent.setup()
    vi.mocked(createAppointment).mockResolvedValue(appointment)
    renderPage(<BookingPage />)
    await user.click(await screen.findByRole('button', { name: 'Chọn khung giờ' }))
    await user.click(screen.getByLabelText(/Tôi đã kiểm tra/))
    await user.click(screen.getByRole('button', { name: 'Xác nhận đặt lịch' }))
    await waitFor(() => expect(createAppointment).toHaveBeenCalledWith(slot.id))
    expect(await screen.findByText(/Đặt lịch thành công/)).toBeInTheDocument()
  })

  it('shows the backend 409 booking conflict', async () => {
    const user = userEvent.setup()
    vi.mocked(createAppointment).mockRejectedValue(axiosError(409, 'Khung giờ vừa được người khác đặt.'))
    renderPage(<BookingPage />)
    await user.click(await screen.findByRole('button', { name: 'Chọn khung giờ' }))
    await user.click(screen.getByLabelText(/Tôi đã kiểm tra/))
    await user.click(screen.getByRole('button', { name: 'Xác nhận đặt lịch' }))
    expect(await screen.findByText('Khung giờ vừa được người khác đặt.')).toBeInTheDocument()
  })

  it('cancels a patient appointment with a reason', async () => {
    const user = userEvent.setup()
    vi.mocked(cancelAppointment).mockResolvedValue({ ...appointment, status: 'CANCELLED' })
    renderPage(<PatientAppointmentsPage />)
    await user.click(await screen.findByRole('button', { name: 'Hủy lịch' }))
    await user.type(screen.getByLabelText('Lý do hủy'), 'Không thể đến khám')
    await user.click(screen.getByRole('button', { name: 'Xác nhận hủy' }))
    await waitFor(() => expect(cancelAppointment).toHaveBeenCalledWith(appointment.id, 'Không thể đến khám'))
  })

  it('lets the assigned doctor set an appointment outcome', async () => {
    const user = userEvent.setup()
    vi.mocked(setAppointmentOutcome).mockResolvedValue({ ...appointment, status: 'COMPLETED' })
    renderPage(<DoctorAppointmentsPage />)
    await user.click(await screen.findByRole('button', { name: 'Đã khám' }))
    await waitFor(() => expect(setAppointmentOutcome).toHaveBeenCalledWith(appointment.id, 'COMPLETED'))
  })

  it('creates a medical record with all four clinical fields', async () => {
    const user = userEvent.setup()
    vi.mocked(getMedicalRecordByAppointment).mockRejectedValue(axiosError(404, 'Không có hồ sơ.'))
    vi.mocked(createMedicalRecord).mockResolvedValue(medicalRecord)
    renderPage(
      <Routes><Route path="/doctor/appointments/:appointmentId/medical-record" element={<DoctorMedicalRecordPage />} /></Routes>,
      `/doctor/appointments/${appointment.id}/medical-record`,
    )
    await screen.findByText('Lập hồ sơ khám')
    await user.type(screen.getByLabelText('Triệu chứng ghi nhận'), 'Mệt nhẹ')
    await user.type(screen.getByLabelText('Ghi chú khám'), 'Ghi chú demo')
    await user.type(screen.getByLabelText('Kết luận do bác sĩ nhập'), 'Theo dõi sức khỏe')
    await user.type(screen.getByLabelText('Hướng dẫn sau khám'), 'Tái khám khi cần')
    await user.click(screen.getByRole('button', { name: 'Tạo hồ sơ khám' }))
    await waitFor(() => expect(createMedicalRecord).toHaveBeenCalledWith(expect.objectContaining({ appointment_id: appointment.id, symptoms: 'Mệt nhẹ' })))
  })

  it('renders patient medical history as read-only', async () => {
    renderPage(<PatientMedicalHistoryPage />)
    expect(await screen.findByText('Theo dõi sức khỏe')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.getByText(/Patient · Chỉ đọc/)).toBeInTheDocument()
  })

  it('shows a loading state while a query is pending', () => {
    vi.mocked(listSpecialties).mockReturnValue(new Promise(() => undefined))
    renderPage(<SpecialtyListPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Đang tải dữ liệu')
  })

  it('shows an empty state', async () => {
    vi.mocked(listSpecialties).mockResolvedValue([])
    renderPage(<SpecialtyListPage />)
    expect(await screen.findByText('Chưa có chuyên khoa')).toBeInTheDocument()
  })

  it('shows a safe API error without a stack trace', async () => {
    vi.mocked(listSpecialties).mockRejectedValue(axiosError(403, 'Bạn không có quyền xem dữ liệu này.'))
    renderPage(<SpecialtyListPage />)
    expect(await screen.findByText('Bạn không có quyền xem dữ liệu này.')).toBeInTheDocument()
    expect(screen.queryByText(/at .*\.tsx/)).not.toBeInTheDocument()
  })
})
