import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from '../features/chat/ChatPage'
import { SpeakButton, VoiceControls } from '../features/chat/VoiceControls'
import { sendChatMessage, transcribeAudio } from '../features/chat/api'
import { useHandoffRealtime } from '../features/handoffs/useHandoffRealtime'
import { renderPage } from './render'

vi.mock('../features/chat/api', async () => {
  const actual = await vi.importActual('../features/chat/api')
  return { ...actual, sendChatMessage: vi.fn(), transcribeAudio: vi.fn() }
})

class MediaRecorderMock {
  static isTypeSupported = vi.fn(() => true)
  state: RecordingState = 'inactive'
  mimeType = 'audio/webm'
  ondataavailable: ((event: BlobEvent) => void) | null = null
  onstop: (() => void) | null = null
  constructor(...args: [MediaStream, MediaRecorderOptions?]) { void args }
  start() { this.state = 'recording' }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['voice'], { type: this.mimeType }) } as BlobEvent)
    this.onstop?.()
  }
}

const stopTrack = vi.fn()
const getUserMedia = vi.fn()

function installRecorder() {
  getUserMedia.mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] })
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia },
  })
  vi.stubGlobal('MediaRecorder', MediaRecorderMock)
}

describe('Phase 11 push-to-talk and browser TTS', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    installRecorder()
  })

  afterEach(() => vi.unstubAllGlobals())

  it('records real Browser API audio, uploads the Blob and returns transcript to text input', async () => {
    vi.mocked(transcribeAudio).mockResolvedValue({
      transcript: 'Tôi cần tìm bác sĩ tim mạch', language: 'vi', duration_seconds: 1,
    })
    vi.mocked(sendChatMessage).mockResolvedValue({ answer: 'Đã nhận câu hỏi.', sources: [] })
    renderPage(<ChatPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Ghi âm' }))
    expect(await screen.findByText(/Đang ghi âm/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dừng ghi âm' }))

    expect(await screen.findByText(/Đã nhận dạng/)).toBeInTheDocument()
    expect(screen.getByLabelText('Tin nhắn')).toHaveValue('Tôi cần tìm bác sĩ tim mạch')
    expect(stopTrack).toHaveBeenCalled()
    expect(transcribeAudio).toHaveBeenCalledWith(expect.any(Blob))

    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }))
    await waitFor(() => expect(sendChatMessage).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Tôi cần tìm bác sĩ tim mạch' }),
      expect.anything(),
    ))
  })

  it('shows permission denial and keeps text input usable', async () => {
    getUserMedia.mockRejectedValue(new DOMException('denied', 'NotAllowedError'))
    renderPage(<ChatPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Ghi âm' }))
    expect(await screen.findByText(/Quyền microphone đã bị từ chối/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Tin nhắn'), { target: { value: 'Tôi vẫn nhập văn bản' } })
    expect(screen.getByLabelText('Tin nhắn')).toHaveValue('Tôi vẫn nhập văn bản')
  })

  it('reports an unavailable microphone and keeps text fallback', async () => {
    getUserMedia.mockRejectedValue(new DOMException('missing', 'NotFoundError'))
    renderPage(<VoiceControls onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ghi âm' }))
    expect(await screen.findByText(/Không tìm thấy hoặc không thể mở microphone/)).toBeInTheDocument()
  })

  it('falls back to text when the browser mediaDevices API is unavailable', () => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: undefined })
    renderPage(<VoiceControls onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ghi âm' }))
    expect(screen.getByText(/không hỗ trợ ghi âm/)).toBeInTheDocument()
  })

  it('falls back to text when MediaRecorder is unsupported', () => {
    vi.stubGlobal('MediaRecorder', undefined)
    renderPage(<VoiceControls onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Ghi âm' }))
    expect(screen.getByText(/không hỗ trợ ghi âm/)).toBeInTheDocument()
  })

  it('uses Browser SpeechSynthesis and supports stop', () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    const utterances: Array<{ text: string }> = []
    class UtteranceMock {
      lang = ''
      voice: SpeechSynthesisVoice | null = null
      onend: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor(public text: string) { utterances.push(this) }
    }
    vi.stubGlobal('SpeechSynthesisUtterance', UtteranceMock)
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: { speak, cancel, getVoices: () => [{ lang: 'vi-VN', name: 'Vietnamese' }] },
    })
    renderPage(<SpeakButton text="Xin chào" />)
    fireEvent.click(screen.getByRole('button', { name: 'Đọc câu trả lời' }))
    expect(speak).toHaveBeenCalled()
    expect(utterances[0].text).toBe('Xin chào')
    fireEvent.click(screen.getByRole('button', { name: 'Dừng đọc' }))
    expect(cancel).toHaveBeenCalledTimes(2)
  })

  it('keeps response text visible when TTS is unavailable', () => {
    vi.stubGlobal('SpeechSynthesisUtterance', undefined)
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: undefined })
    renderPage(<SpeakButton text="Nội dung vẫn hiển thị" />)
    expect(screen.getByText(/TTS không khả dụng/)).toBeInTheDocument()
  })
})

class WebSocketMock {
  static instances: WebSocketMock[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  constructor(public url: string) { WebSocketMock.instances.push(this) }
  close() {}
}

function RealtimeHarness() {
  const state = useHandoffRealtime(true)
  return <div>{state}</div>
}

function queryWrapper(client: QueryClient, children: ReactNode) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('Phase 11 Handoff WebSocket', () => {
  beforeEach(() => {
    WebSocketMock.instances = []
    vi.stubGlobal('WebSocket', WebSocketMock)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reloads authoritative REST state on connect, events and reconnect', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidate = vi.spyOn(client, 'invalidateQueries').mockResolvedValue()
    const view = render(queryWrapper(client, <RealtimeHarness />))
    const first = WebSocketMock.instances[0]
    expect(first.url).toBe('ws://localhost:8000/api/v1/handoffs/ws')

    act(() => first.onopen?.())
    expect(screen.getByText('connected')).toBeInTheDocument()
    expect(invalidate).toHaveBeenCalledTimes(1)

    act(() => first.onmessage?.({ data: JSON.stringify({ type: 'handoff.created' }) } as MessageEvent))
    expect(invalidate).toHaveBeenCalledTimes(2)

    act(() => first.onclose?.())
    expect(screen.getByText('reconnecting')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(1000))
    const second = WebSocketMock.instances[1]
    act(() => second.onopen?.())
    expect(invalidate).toHaveBeenCalledTimes(3)
    view.unmount()
  })
})
