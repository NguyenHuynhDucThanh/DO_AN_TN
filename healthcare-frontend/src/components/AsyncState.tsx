import { Alert, Button, CircularProgress, Stack, Typography } from '@mui/material'
import { parseApiError } from '../api/errors'

export function LoadingState({ label = 'Đang tải dữ liệu…' }: { label?: string }) {
  return (
    <Stack role="status" spacing={2} sx={{ py: 8, alignItems: 'center' }}>
      <CircularProgress size={32} />
      <Typography color="text.secondary">{label}</Typography>
    </Stack>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const parsed = parseApiError(error)
  return (
    <Alert
      severity="error"
      action={onRetry ? <Button onClick={onRetry}>Thử lại</Button> : undefined}
    >
      {parsed.message}
    </Alert>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Stack spacing={1} sx={{ py: 7, px: 2, textAlign: 'center', alignItems: 'center' }}>
      <Typography variant="h3">{title}</Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 520 }}>{description}</Typography>
    </Stack>
  )
}
