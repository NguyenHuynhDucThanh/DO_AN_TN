import { ThemeProvider } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DoctorAdminPage } from '../features/doctors/DoctorAdminPage'
import { createDoctor, listDoctorCandidates, listDoctors, provisionDoctor } from '../features/doctors/api'
import { DoctorSchedulesPage } from '../features/schedules/DoctorSchedulesPage'
import { createSchedule, generateSlots, listScheduleSlots, listSchedules, setSlotStatus } from '../features/schedules/api'
import { listSpecialties } from '../features/specialties/api'
import { theme } from '../theme/theme'
import type { Doctor, Schedule, Slot, Specialty } from '../types/domain'

vi.mock('../features/auth/AuthContext', () => ({
  useAuth: () => ({ user: { id: '33333333-3333-4333-8333-333333333333', roles: ['DOCTOR'] } }),
}))
vi.mock('../features/specialties/api', () => ({
  specialtyKeys: { all: ['specialties'] }, listSpecialties: vi.fn(),
}))
vi.mock('../features/doctors/api', () => ({
  doctorKeys: { all: ['doctors'], candidates: ['doctors', 'candidates'], detail: (id: string) => ['doctors', id] },
  listDoctors: vi.fn(), listDoctorCandidates: vi.fn(), createDoctor: vi.fn(), provisionDoctor: vi.fn(), updateDoctor: vi.fn(),
}))
vi.mock('../features/schedules/api', () => ({
  scheduleKeys: {
    all: ['schedules'], byDoctor: (id: string) => ['schedules', 'doctor', id],
    slots: (id: string) => ['schedules', id, 'slots'], available: (filters: object) => ['slots', 'available', filters],
  },
  listSchedules: vi.fn(), listScheduleSlots: vi.fn(), listAvailableSlots: vi.fn(), createSchedule: vi.fn(),
  updateSchedule: vi.fn(), generateSlots: vi.fn(), setSlotStatus: vi.fn(),
}))

const specialty: Specialty = {
  id: '11111111-1111-4111-8111-111111111111', code: 'NOI', name: 'Nội tổng quát', description: null,
  is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}
const doctor: Doctor = {
  id: '22222222-2222-4222-8222-222222222222', user_id: '33333333-3333-4333-8333-333333333333', specialty_id: specialty.id,
  license_number: 'DEMO-01', biography: null, is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  user: { id: '33333333-3333-4333-8333-333333333333', full_name: 'Bác sĩ An', email: 'doctor@example.invalid', phone: '0900000000' },
  specialty: { id: specialty.id, code: specialty.code, name: specialty.name },
}
const schedule: Schedule = {
  id: '44444444-4444-4444-8444-444444444444', doctor_id: doctor.id,
  start_at: '2031-01-10T01:00:00Z', end_at: '2031-01-10T03:00:00Z', slot_duration_minutes: 30,
  status: 'ACTIVE', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}
const slot: Slot = {
  id: '55555555-5555-4555-8555-555555555555', schedule_id: schedule.id,
  start_at: schedule.start_at, end_at: '2031-01-10T01:30:00Z', status: 'AVAILABLE',
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

function renderPage(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><ThemeProvider theme={theme}><MemoryRouter>{ui}</MemoryRouter></ThemeProvider></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listSpecialties).mockResolvedValue([specialty])
  vi.mocked(listDoctors).mockResolvedValue([doctor])
  vi.mocked(listDoctorCandidates).mockResolvedValue([{ id: '66666666-6666-4666-8666-666666666666', full_name: 'Bác sĩ Chưa Gắn', email: 'candidate@example.invalid', phone: null }])
  vi.mocked(provisionDoctor).mockResolvedValue(doctor)
  vi.mocked(createDoctor).mockResolvedValue(doctor)
  vi.mocked(listSchedules).mockResolvedValue([])
  vi.mocked(listScheduleSlots).mockResolvedValue([])
  vi.mocked(createSchedule).mockResolvedValue(schedule)
  vi.mocked(generateSlots).mockResolvedValue([slot])
  vi.mocked(setSlotStatus).mockResolvedValue({ ...slot, status: 'BLOCKED' })
})

describe('Post Phase 14 doctor and schedule workflows', () => {
  it('provisions a Doctor account and profile from one Admin dialog', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorAdminPage />)
    await user.click(await screen.findByRole('button', { name: 'Thêm bác sĩ' }))
    await user.type(screen.getByLabelText('Họ và tên'), 'Bác sĩ Bình')
    await user.type(screen.getByLabelText('Email'), 'binh@example.invalid')
    await user.type(screen.getByLabelText('Số điện thoại'), '0901234567')
    await user.type(screen.getByLabelText('Mật khẩu tạm thời'), 'Temporary123')
    await user.type(screen.getByLabelText('Xác nhận mật khẩu'), 'Temporary123')
    await user.click(screen.getByLabelText('Chuyên khoa'))
    await user.click(await screen.findByRole('option', { name: specialty.name }))
    await user.type(screen.getByLabelText('Số giấy phép'), 'GL-001')
    await user.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(provisionDoctor).toHaveBeenCalledWith(expect.objectContaining({ email: 'binh@example.invalid', specialty_id: specialty.id, license_number: 'GL-001' })))
  })

  it('selects an existing Doctor account without exposing a UUID field', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorAdminPage />)
    await user.click(await screen.findByRole('button', { name: 'Thêm bác sĩ' }))
    await user.click(screen.getByLabelText('Tài khoản'))
    await user.click(await screen.findByRole('option', { name: 'Dùng tài khoản bác sĩ có sẵn' }))
    expect(screen.queryByLabelText('User UUID')).not.toBeInTheDocument()
    await user.click(screen.getByLabelText('Tài khoản bác sĩ'))
    await user.click(await screen.findByRole('option', { name: /Bác sĩ Chưa Gắn/ }))
    await user.click(screen.getByLabelText('Chuyên khoa'))
    await user.click(await screen.findByRole('option', { name: specialty.name }))
    await user.type(screen.getByLabelText('Số giấy phép'), 'GL-002')
    await user.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(createDoctor).toHaveBeenCalledWith(expect.objectContaining({ user_id: '66666666-6666-4666-8666-666666666666' })))
  })

  it('creates a future schedule from the Doctor page', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorSchedulesPage />)
    await user.click(await screen.findByRole('button', { name: 'Tạo lịch' }))
    fireEvent.change(screen.getByLabelText('Bắt đầu'), { target: { value: '2031-01-10T08:00' } })
    fireEvent.change(screen.getByLabelText('Kết thúc'), { target: { value: '2031-01-10T10:00' } })
    fireEvent.change(screen.getByLabelText('Thời lượng mỗi khung giờ (phút)'), { target: { value: '30' } })
    await user.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(createSchedule).toHaveBeenCalledWith(expect.objectContaining({ doctor_id: doctor.id, slot_duration_minutes: 30 })))
  })

  it('generates and blocks slots through the existing schedule services', async () => {
    const user = userEvent.setup()
    vi.mocked(listSchedules).mockResolvedValue([schedule])
    const first = renderPage(<DoctorSchedulesPage />)
    await user.click(await screen.findByRole('button', { name: 'Tạo khung giờ' }))
    await waitFor(() => expect(generateSlots).toHaveBeenCalledWith(schedule.id))
    first.unmount()

    vi.mocked(listScheduleSlots).mockResolvedValue([slot])
    const second = renderPage(<DoctorSchedulesPage />)
    await user.click(await screen.findByRole('button', { name: 'Chặn' }))
    await waitFor(() => expect(setSlotStatus).toHaveBeenCalledWith(slot.id, true))
    second.unmount()
  })
})
