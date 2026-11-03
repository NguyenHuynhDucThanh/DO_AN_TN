import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from '../features/chat/ChatPage'
import { sendChatMessage } from '../features/chat/api'
import { renderPage } from './render'

vi.mock('../features/chat/api', async () => {
  const actual = await vi.importActual('../features/chat/api')
  return { ...actual, sendChatMessage: vi.fn() }
})

function apiError(code: string, detail: string) {
  return Object.assign(new Error(detail), {
    isAxiosError: true,
    response: { status: 503, data: { error: { code, detail } } },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Phase 7 Gemini basic chatbot UI', () => {
  it('sends text and renders a stable chatbot response', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({ answer: 'Hãy chuẩn bị giấy tờ và thông tin cần trao đổi.', sources: [] })
    const user = userEvent.setup()
    renderPage(<ChatPage />)

    await user.type(screen.getByLabelText('Tin nhắn'), 'Tôi nên chuẩn bị gì trước khi khám?')
    await user.click(screen.getByRole('button', { name: 'Gửi' }))

    await waitFor(() => expect(vi.mocked(sendChatMessage).mock.calls[0]?.[0]).toEqual({
      message: 'Tôi nên chuẩn bị gì trước khi khám?',
      history: [],
      use_rag: true,
    }))
    expect(screen.getByText('Tôi nên chuẩn bị gì trước khi khám?')).toBeInTheDocument()
    expect(await screen.findByText('Hãy chuẩn bị giấy tờ và thông tin cần trao đổi.')).toBeInTheDocument()
  })

  it('keeps only lightweight UI history in the next request', async () => {
    vi.mocked(sendChatMessage)
      .mockResolvedValueOnce({ answer: 'Câu trả lời thứ nhất.', sources: [] })
      .mockResolvedValueOnce({ answer: 'Câu trả lời thứ hai.', sources: [] })
    const user = userEvent.setup()
    renderPage(<ChatPage />)

    await user.type(screen.getByLabelText('Tin nhắn'), 'Câu hỏi thứ nhất')
    await user.click(screen.getByRole('button', { name: 'Gửi' }))
    await screen.findByText('Câu trả lời thứ nhất.')
    await user.type(screen.getByLabelText('Tin nhắn'), 'Câu hỏi thứ hai')
    await user.click(screen.getByRole('button', { name: 'Gửi' }))

    await waitFor(() => expect(vi.mocked(sendChatMessage).mock.calls.at(-1)?.[0]).toEqual({
      message: 'Câu hỏi thứ hai',
      history: [
        { role: 'user', content: 'Câu hỏi thứ nhất' },
        { role: 'assistant', content: 'Câu trả lời thứ nhất.' },
      ],
      use_rag: true,
    }))
  })

  it('validates empty input without calling the Backend', async () => {
    const user = userEvent.setup()
    renderPage(<ChatPage />)
    await user.click(screen.getByRole('button', { name: 'Gửi' }))
    expect(await screen.findByText('Hãy nhập nội dung cần hỏi.')).toBeInTheDocument()
    expect(sendChatMessage).not.toHaveBeenCalled()
  })

  it('shows loading, safe unavailable feedback, and retries', async () => {
    vi.mocked(sendChatMessage)
      .mockRejectedValueOnce(apiError('chatbot_rate_limited', 'raw provider detail must not render'))
      .mockResolvedValueOnce({ answer: 'Chatbot đã hoạt động lại.', sources: [] })
    const user = userEvent.setup()
    renderPage(<ChatPage />)

    await user.type(screen.getByLabelText('Tin nhắn'), 'Xin chào')
    await user.click(screen.getByRole('button', { name: 'Gửi' }))

    expect(await screen.findByText(/Chatbot tạm thời không khả dụng/)).toBeInTheDocument()
    expect(screen.queryByText('raw provider detail must not render')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Thử lại' }))
    expect(await screen.findByText('Chatbot đã hoạt động lại.')).toBeInTheDocument()
    expect(sendChatMessage).toHaveBeenCalledTimes(2)
  })
})
