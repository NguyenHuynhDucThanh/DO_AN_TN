import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Box, Button, CircularProgress, Divider, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { parseApiError } from '../../api/errors'
import { PageHeader } from '../../components/PageHeader'
import {
  confirmChatBooking,
  sendChatMessage,
  type BookingConfirmation,
  type ChatMessage,
  type ChatRequest,
  type ChatSource,
  type RiskAlert,
  type ToolResult,
} from './api'
import { SpeakButton, VoiceControls } from './VoiceControls'

const chatSchema = z.object({
  message: z.string().trim().min(1, 'Hãy nhập nội dung cần hỏi.').max(4000, 'Tin nhắn tối đa 4.000 ký tự.'),
})

type ChatForm = z.infer<typeof chatSchema>
type UiChatMessage = ChatMessage & {
  sources?: ChatSource[]
  toolResults?: ToolResult[]
  riskAlert?: RiskAlert | null
}

function toolItemLabel(item: unknown): string | null {
  if (!item || typeof item !== 'object') return null
  const value = item as Record<string, unknown>
  if (typeof value.start_at === 'string') {
    const time = new Date(value.start_at).toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
    return `${String(value.doctor_name ?? 'Bác sĩ')} · ${time} · Slot ${String(value.slot_id ?? '')}`
  }
  if (typeof value.full_name === 'string') {
    return `${value.full_name}${typeof value.specialty_name === 'string' ? ` · ${value.specialty_name}` : ''}`
  }
  if (typeof value.name === 'string') return value.name
  return null
}

export function ChatPage() {
  const [messages, setMessages] = useState<UiChatMessage[]>([])
  const [lastRequest, setLastRequest] = useState<ChatRequest | null>(null)
  const [confirmation, setConfirmation] = useState<BookingConfirmation | null>(null)
  const { control, handleSubmit, reset, setValue } = useForm<ChatForm>({
    resolver: zodResolver(chatSchema),
    defaultValues: { message: '' },
  })
  const mutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (response) => {
      setMessages((current) => [...current, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        toolResults: response.tool_results,
        riskAlert: response.risk_alert,
      }])
      setConfirmation(response.booking_confirmation ?? null)
    },
  })
  const confirmMutation = useMutation({
    mutationFn: confirmChatBooking,
    onSuccess: (response) => {
      setConfirmation(null)
      setMessages((current) => [...current, {
        role: 'assistant',
        content: `Đặt lịch thành công. Mã lịch hẹn: ${response.appointment_id}`,
      }])
    },
  })

  const submit = handleSubmit(({ message }) => {
    const payload: ChatRequest = {
      message: message.trim(),
      history: messages.slice(-10).map(({ role, content }) => ({ role, content })),
      use_rag: true,
    }
    setMessages((current) => [...current, { role: 'user', content: payload.message }])
    setLastRequest(payload)
    mutation.mutate(payload)
    reset()
  })

  const retry = () => {
    if (lastRequest) mutation.mutate(lastRequest)
  }
  const parsedError = mutation.error ? parseApiError(mutation.error) : null
  const unavailable = parsedError?.code?.startsWith('chatbot_') || parsedError?.code?.startsWith('rag_')

  return (
    <Stack spacing={3} sx={{ maxWidth: 900, mx: 'auto' }}>
      <PageHeader
        eyebrow="AI MVP + VOICE · PHASE 11"
        title="Chatbot thông tin sức khỏe"
        description="AI MVP thống nhất: tra cứu nguồn đã duyệt, dữ liệu nghiệp vụ thật, xác nhận đặt lịch bắt buộc và cảnh báo an toàn dựa trên rule độc lập Gemini."
      />

      <Alert severity="info">
        Chatbot không thay thế bác sĩ, không chẩn đoán và không kê đơn. Không nhập thông tin định danh hoặc nội dung hồ sơ khám riêng tư.
      </Alert>

      <Paper variant="outlined" sx={{ minHeight: 360, maxHeight: 560, overflowY: 'auto', p: { xs: 2, md: 3 } }}>
        {messages.length === 0 ? (
          <Stack sx={{ minHeight: 300, justifyContent: 'center', textAlign: 'center' }}>
            <Typography variant="h3">Bắt đầu cuộc trò chuyện</Typography>
            <Typography color="text.secondary">Hãy hỏi một câu về thông tin sức khỏe phổ thông.</Typography>
          </Stack>
        ) : (
          <Stack spacing={2} aria-label="Danh sách tin nhắn">
            {messages.map((message, index) => (
              <Box
                key={`${message.role}-${index}`}
                sx={{
                  alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: { xs: '92%', md: '78%' },
                  bgcolor: message.role === 'user' ? 'primary.main' : 'grey.100',
                  color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                  px: 2,
                  py: 1.5,
                  borderRadius: 2,
                  whiteSpace: 'pre-wrap',
                  overflowWrap: 'anywhere',
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {message.role === 'user' ? 'Bạn' : 'Chatbot'}
                </Typography>
                {message.riskAlert ? (
                  <Alert severity="error" aria-label="Cảnh báo an toàn khẩn cấp">
                    <Typography sx={{ fontWeight: 700 }}>{message.riskAlert.title}</Typography>
                    <Typography>{message.riskAlert.message}</Typography>
                    <Box component="ul" sx={{ pl: 2.5, my: 1 }}>
                      {message.riskAlert.recommended_actions.map((action) => (
                        <li key={action}><Typography variant="body2">{action}</Typography></li>
                      ))}
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {message.riskAlert.handoff.status === 'PENDING'
                        ? 'Handoff: đang chờ nhân viên tiếp nhận.'
                        : 'Handoff: chưa thể tạo tự động.'}
                    </Typography>
                    <Typography variant="caption">{message.riskAlert.handoff.message}</Typography>
                  </Alert>
                ) : (
                  <Typography>{message.content}</Typography>
                )}
                {message.role === 'assistant' && message.toolResults && message.toolResults.length > 0 && (
                  <Stack spacing={0.75} sx={{ mt: 1.5 }} aria-label="Kết quả công cụ">
                    {message.toolResults.map((result, resultIndex) => (
                      <Box key={`${result.name}-${resultIndex}`}>
                        <Typography variant="caption">
                          {result.name}: {result.status === 'SUCCESS' ? 'đã lấy dữ liệu thật' : 'cần xác nhận'}
                          {typeof result.data.count === 'number' ? ` · ${result.data.count} kết quả` : ''}
                        </Typography>
                        {Array.isArray(result.data.items) && result.data.items.map((item, itemIndex) => {
                          const label = toolItemLabel(item)
                          return label ? <Typography key={itemIndex} variant="body2">• {label}</Typography> : null
                        })}
                        {Array.isArray(result.data.items) && result.data.items.length === 0 && (
                          <Typography variant="body2">Không có kết quả phù hợp.</Typography>
                        )}
                      </Box>
                    ))}
                  </Stack>
                )}
                {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                  <Stack spacing={0.75} sx={{ mt: 1.5 }} aria-label="Nguồn tham khảo">
                    <Typography variant="caption" sx={{ fontWeight: 700 }}>Nguồn tham khảo</Typography>
                    {message.sources.map((source, sourceIndex) => (
                      <Box key={`${source.document_id}-${source.article_id ?? source.page ?? sourceIndex}`}>
                    <Typography variant="caption" sx={{ display: 'block' }}>
                          {source.title ?? source.source_name ?? 'Tài liệu đã phê duyệt'}
                          {source.category ? ` · ${source.category}` : ''}
                          {source.page ? ` · Trang ${source.page}` : ''}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                )}
                {message.role === 'assistant' && <SpeakButton text={message.content} />}
              </Box>
            ))}
            {mutation.isPending && (
              <Stack role="status" direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                <CircularProgress size={20} />
                <Typography color="text.secondary">Chatbot đang trả lời…</Typography>
              </Stack>
            )}
          </Stack>
        )}
      </Paper>

      {confirmation && (
        <Paper variant="outlined" sx={{ p: 2.5 }} aria-label="Xác nhận đặt lịch">
          <Stack spacing={1.25}>
            <Typography variant="h3">Xác nhận đặt lịch</Typography>
            <Divider />
            <Typography><strong>Bác sĩ:</strong> {confirmation.doctor_name}</Typography>
            <Typography><strong>Chuyên khoa:</strong> {confirmation.specialty_name}</Typography>
            <Typography><strong>Ngày:</strong> {new Date(confirmation.start_at).toLocaleDateString('vi-VN')}</Typography>
            <Typography>
              <strong>Thời gian:</strong>{' '}
              {new Date(confirmation.start_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
              {' – '}
              {new Date(confirmation.end_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
            </Typography>
            <Typography variant="caption">Slot: {confirmation.slot_id}</Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button
                variant="contained"
                disabled={confirmMutation.isPending}
                onClick={() => confirmMutation.mutate(confirmation.confirmation_token)}
              >
                {confirmMutation.isPending ? 'Đang đặt lịch…' : 'Xác nhận đặt lịch'}
              </Button>
              <Button disabled={confirmMutation.isPending} onClick={() => setConfirmation(null)}>
                Không đặt
              </Button>
            </Stack>
          </Stack>
        </Paper>
      )}

      {confirmMutation.error && (
        <Alert severity="error">
          {parseApiError(confirmMutation.error).status === 409
            ? 'Slot này vừa được người khác đặt. Hãy yêu cầu chatbot tìm slot khác.'
            : parseApiError(confirmMutation.error).message}
        </Alert>
      )}

      {parsedError && (
        <Alert
          severity="error"
          action={<Button onClick={retry} disabled={mutation.isPending}>Thử lại</Button>}
        >
          {unavailable ? 'Chatbot tạm thời không khả dụng. Các chức năng đặt lịch và tra cứu thủ công vẫn hoạt động.' : parsedError.message}
        </Alert>
      )}

      <Box component="form" onSubmit={submit} noValidate>
        <Box sx={{ mb: 2 }}>
          <VoiceControls onTranscript={(transcript) => setValue('message', transcript, { shouldValidate: true })} />
        </Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'flex-start' } }}>
          <Controller
            name="message"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Tin nhắn"
                placeholder="Ví dụ: Tôi nên chuẩn bị gì trước khi đi khám?"
                multiline
                minRows={2}
                fullWidth
                disabled={mutation.isPending}
                error={Boolean(fieldState.error)}
                helperText={fieldState.error?.message ?? 'Tối đa 4.000 ký tự; chỉ dùng dữ liệu demo/không nhạy cảm.'}
              />
            )}
          />
          <Button type="submit" variant="contained" size="large" disabled={mutation.isPending} sx={{ minWidth: 120, minHeight: 56 }}>
            {mutation.isPending ? 'Đang gửi…' : 'Gửi'}
          </Button>
        </Stack>
      </Box>
    </Stack>
  )
}
