import { Alert, Button, CircularProgress, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { parseApiError } from '../../api/errors'
import { transcribeAudio } from './api'

type VoiceState = 'idle' | 'requesting' | 'recording' | 'processing' | 'success' | 'error'

function preferredMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus']
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate))
}

export function VoiceControls({ onTranscript }: { onTranscript: (transcript: string) => void }) {
  const [state, setState] = useState<VoiceState>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const cleanupStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  useEffect(() => () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    cleanupStream()
  }, [])

  const supported = Boolean(
    'mediaDevices' in navigator
    && typeof navigator.mediaDevices?.getUserMedia === 'function'
    && typeof (window as unknown as { MediaRecorder?: unknown }).MediaRecorder === 'function',
  )

  const start = async () => {
    if (!supported) {
      setState('error')
      setMessage('Trình duyệt hoặc thiết bị không hỗ trợ ghi âm. Bạn vẫn có thể nhập văn bản.')
      return
    }
    setState('requesting')
    setMessage(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      const mimeType = preferredMimeType()
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      recorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = async () => {
        cleanupStream()
        const type = recorder.mimeType || chunksRef.current[0]?.type || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type })
        chunksRef.current = []
        if (blob.size === 0) {
          setState('error')
          setMessage('Không thu được âm thanh. Hãy thử lại hoặc nhập văn bản.')
          return
        }
        setState('processing')
        try {
          const result = await transcribeAudio(blob)
          onTranscript(result.transcript)
          setState('success')
          setMessage(`Đã nhận dạng: ${result.transcript}`)
        } catch (error) {
          setState('error')
          setMessage(`${parseApiError(error).message} Bạn vẫn có thể nhập văn bản.`)
        }
      }
      recorder.start()
      setState('recording')
      setMessage('Đang ghi âm từ microphone của thiết bị…')
    } catch (error) {
      cleanupStream()
      setState('error')
      const denied = error instanceof DOMException && ['NotAllowedError', 'SecurityError'].includes(error.name)
      setMessage(denied
        ? 'Quyền microphone đã bị từ chối. Hãy cấp quyền trong trình duyệt hoặc tiếp tục nhập văn bản.'
        : 'Không tìm thấy hoặc không thể mở microphone. Bạn vẫn có thể nhập văn bản.')
    }
  }

  const stop = () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  return (
    <Stack spacing={1} aria-label="Điều khiển giọng nói">
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
        {state !== 'recording' ? (
          <Button variant="outlined" onClick={start} disabled={state === 'requesting' || state === 'processing'}>
            {state === 'requesting' ? 'Đang xin quyền…' : 'Ghi âm'}
          </Button>
        ) : (
          <Button variant="contained" color="error" onClick={stop}>Dừng ghi âm</Button>
        )}
        {(state === 'requesting' || state === 'processing') && <CircularProgress size={20} />}
        <Typography variant="caption">Push-to-talk tiếng Việt; audio chỉ dùng để nhận dạng và không được lưu lâu dài.</Typography>
      </Stack>
      {message && <Alert severity={state === 'error' ? 'error' : state === 'success' ? 'success' : 'info'}>{message}</Alert>}
    </Stack>
  )
}

export function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false)
  const available = typeof window.speechSynthesis?.speak === 'function'
    && typeof (window as unknown as { SpeechSynthesisUtterance?: unknown }).SpeechSynthesisUtterance === 'function'

  const speak = () => {
    if (!available) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    const vietnameseVoice = window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase().startsWith('vi'))
    if (vietnameseVoice) utterance.voice = vietnameseVoice
    utterance.lang = vietnameseVoice?.lang ?? 'vi-VN'
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  const stop = () => {
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  if (!available) return <Typography variant="caption">TTS không khả dụng; nội dung văn bản vẫn hiển thị.</Typography>
  return speaking
    ? <Button size="small" onClick={stop}>Dừng đọc</Button>
    : <Button size="small" onClick={speak}>Đọc câu trả lời</Button>
}
