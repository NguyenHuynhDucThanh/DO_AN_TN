import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from '../features/chat/ChatPage'
import { sendChatMessage } from '../features/chat/api'
import { renderPage } from './render'

vi.mock('../features/chat/api', async () => {
  const actual = await vi.importActual('../features/chat/api')
  return { ...actual, sendChatMessage: vi.fn() }
})

const baseAlert = {
  level: 'URGENT' as const,
  title: 'Cảnh báo an toàn khẩn cấp',
  message: 'Đây là cảnh báo an toàn, không phải chẩn đoán.',
  recommended_actions: [
    'Liên hệ dịch vụ cấp cứu tại nơi bạn đang ở.',
    'Nhờ một người ở gần hỗ trợ.',
  ],
  rule_codes: ['RISK-RESPIRATORY'],
}

describe('Phase 10 Risk Alert UI', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders an urgent rule-based warning and pending handoff state', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: baseAlert.message,
      sources: [],
      tool_results: [{
        name: 'risk_handoff',
        status: 'SUCCESS',
        data: { status: 'PENDING', priority: 'URGENT' },
      }],
      risk_alert: {
        ...baseAlert,
        handoff: {
          status: 'PENDING',
          handoff_id: '11111111-1111-4111-8111-111111111111',
          message: 'Yêu cầu hỗ trợ ưu tiên đã được ghi nhận.',
        },
      },
    })
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Tôi không thở được' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))

    expect(await screen.findByLabelText('Cảnh báo an toàn khẩn cấp')).toBeInTheDocument()
    expect(screen.getByText(/không phải chẩn đoán/)).toBeInTheDocument()
    expect(screen.getByText(/đang chờ nhân viên tiếp nhận/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Xác nhận đặt lịch')).not.toBeInTheDocument()
  })

  it('keeps the safety warning visible when automatic handoff fails', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: baseAlert.message,
      sources: [],
      risk_alert: {
        ...baseAlert,
        handoff: {
          status: 'FAILED',
          message: 'Hãy dùng chức năng liên hệ thủ công và tìm trợ giúp y tế ngay.',
        },
      },
    })
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Đang chảy máu không cầm' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))

    expect(await screen.findByLabelText('Cảnh báo an toàn khẩn cấp')).toBeInTheDocument()
    expect(screen.getByText(/chưa thể tạo tự động/)).toBeInTheDocument()
    expect(screen.getByText(/liên hệ thủ công/)).toBeInTheDocument()
  })
})

