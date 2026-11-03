import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from '../features/chat/ChatPage'
import { confirmChatBooking, sendChatMessage } from '../features/chat/api'
import { renderPage } from './render'

vi.mock('../features/chat/api', async () => {
  const actual = await vi.importActual('../features/chat/api')
  return {
    ...actual,
    sendChatMessage: vi.fn(),
    confirmChatBooking: vi.fn(),
  }
})

const confirmation = {
  status: 'CONFIRMATION_REQUIRED' as const,
  confirmation_token: 'signed-confirmation-token',
  slot_id: '11111111-1111-4111-8111-111111111111',
  doctor_id: '22222222-2222-4222-8222-222222222222',
  doctor_name: 'Bác sĩ Demo',
  specialty_id: '33333333-3333-4333-8333-333333333333',
  specialty_name: 'Tim mạch',
  start_at: '2027-01-10T01:00:00Z',
  end_at: '2027-01-10T01:30:00Z',
}

describe('Phase 9 explicit booking confirmation UI', () => {
  beforeEach(() => vi.clearAllMocks())

  it('does not book from chat text and books only after the button click', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: 'Vui lòng kiểm tra thông tin.',
      sources: [],
      tool_results: [{ name: 'create_booking', status: 'CONFIRMATION_REQUIRED', data: confirmation }],
      booking_confirmation: confirmation,
    })
    vi.mocked(confirmChatBooking).mockResolvedValue({
      status: 'BOOKED',
      appointment_id: '44444444-4444-4444-8444-444444444444',
      slot_id: confirmation.slot_id,
    })
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Đặt slot này' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))

    expect(await screen.findByLabelText('Xác nhận đặt lịch')).toBeInTheDocument()
    expect(screen.getByText('Bác sĩ Demo')).toBeInTheDocument()
    expect(screen.getByText('Tim mạch')).toBeInTheDocument()
    expect(confirmChatBooking).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận đặt lịch' }))
    await waitFor(() => expect(vi.mocked(confirmChatBooking).mock.calls[0]?.[0]).toBe('signed-confirmation-token'))
    expect(await screen.findByText(/Đặt lịch thành công/)).toBeInTheDocument()
  })

  it('shows a controlled 409 conflict and asks for another slot', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: 'Cần xác nhận.',
      sources: [],
      booking_confirmation: confirmation,
    })
    vi.mocked(confirmChatBooking).mockRejectedValue(Object.assign(new Error('private'), {
      isAxiosError: true,
      response: { status: 409, data: { error: { code: 'slot_occupied', detail: 'private' } } },
    }))
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Đặt lịch' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Xác nhận đặt lịch' }))
    expect(await screen.findByText(/Slot này vừa được người khác đặt/)).toBeInTheDocument()
    expect(screen.queryByText('private')).not.toBeInTheDocument()
  })
})

