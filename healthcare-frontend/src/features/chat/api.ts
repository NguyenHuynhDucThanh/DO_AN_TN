import { apiClient } from '../../api/client'

export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  role: ChatRole
  content: string
}

export type ChatRequest = {
  message: string
  history: ChatMessage[]
  use_rag?: boolean
}

export type ChatSource = {
  document_id: string
  title: string | null
  category: string | null
  source_name: string | null
  article_id: string | null
  page: number | null
}

export type ChatResponse = {
  answer: string
  sources: ChatSource[]
  tool_results?: ToolResult[]
  booking_confirmation?: BookingConfirmation | null
  risk_alert?: RiskAlert | null
}

export type RiskAlert = {
  level: 'URGENT'
  title: string
  message: string
  recommended_actions: string[]
  rule_codes: string[]
  handoff: {
    status: 'PENDING' | 'FAILED'
    handoff_id?: string | null
    message: string
  }
}

export type ToolResult = {
  name: string
  status: 'SUCCESS' | 'CONFIRMATION_REQUIRED'
  data: Record<string, unknown>
}

export type BookingConfirmation = {
  status: 'CONFIRMATION_REQUIRED'
  confirmation_token: string
  slot_id: string
  doctor_id: string
  doctor_name: string
  specialty_id: string
  specialty_name: string
  start_at: string
  end_at: string
}

export type BookingConfirmationResponse = {
  status: 'BOOKED'
  appointment_id: string
  slot_id: string
}

export async function sendChatMessage(payload: ChatRequest) {
  // The first Windows CPU request may need to load BGE-M3 into memory before Gemini runs.
  const { data } = await apiClient.post<ChatResponse>('/chat/messages', payload, { timeout: 120_000 })
  return data
}

export async function confirmChatBooking(confirmationToken: string) {
  const { data } = await apiClient.post<BookingConfirmationResponse>('/chat/bookings/confirm', {
    confirmation_token: confirmationToken,
  })
  return data
}

export type TranscriptionResponse = {
  transcript: string
  language: string
  duration_seconds: number | null
}

export async function transcribeAudio(audio: Blob) {
  const form = new FormData()
  const extension = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('wav') ? 'wav' : 'webm'
  form.append('audio', audio, `push-to-talk.${extension}`)
  const { data } = await apiClient.post<TranscriptionResponse>('/voice/transcriptions', form, {
    timeout: 100_000,
  })
  return data
}
