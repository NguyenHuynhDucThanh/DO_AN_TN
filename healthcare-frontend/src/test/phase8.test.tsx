import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from '../features/chat/ChatPage'
import { sendChatMessage } from '../features/chat/api'
import { renderPage } from './render'

vi.mock('../features/chat/api', async () => {
  const actual = await vi.importActual('../features/chat/api')
  return { ...actual, sendChatMessage: vi.fn() }
})

describe('Phase 8 RAG UI', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders traceable sources returned by the backend', async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: 'Thông tin tham khảo an toàn.',
      sources: [{
        document_id: '11111111-1111-4111-8111-111111111111',
        title: 'Tài liệu sức khỏe',
        category: 'kien_thuc_y_khoa',
        source_name: 'vietnamese-medical-dataset',
        article_id: '42',
        page: null,
      }],
    })
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Hay chóng mặt khi đứng lên' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    expect(await screen.findByText('Thông tin tham khảo an toàn.')).toBeInTheDocument()
    expect(screen.getByText('Nguồn tham khảo')).toBeInTheDocument()
    expect(screen.getByText(/Tài liệu sức khỏe.*kien_thuc_y_khoa/)).toBeInTheDocument()
    await waitFor(() => expect(vi.mocked(sendChatMessage).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ use_rag: true }),
    ))
  })

  it('shows controlled RAG unavailable feedback and keeps retry', async () => {
    vi.mocked(sendChatMessage).mockRejectedValue(Object.assign(new Error('private detail'), {
      isAxiosError: true,
      response: { status: 503, data: { error: { code: 'rag_unavailable', detail: 'private detail' } } },
    }))
    renderPage(<ChatPage />)
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Câu hỏi demo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    expect(await screen.findByText(/Chatbot tạm thời không khả dụng/)).toBeInTheDocument()
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Thử lại' })).toBeInTheDocument()
  })
})
