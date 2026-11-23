import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { parseApiError } from '../api/errors'

export function LoadingState({ label = 'Đang tải dữ liệu…' }: { label?: string }) {
  return (
    <Stack role="status" spacing={2} sx={{ py: 9, alignItems: 'center', color: 'text.secondary' }}>
      <CircularProgress size={30} thickness={4} />
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

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <Paper variant="outlined">
      <Stack spacing={1.25} sx={{ py: { xs: 6, md: 8 }, px: 3, textAlign: 'center', alignItems: 'center' }}>
        <Box aria-hidden sx={{ width: 44, height: 44, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: 'primary.light', color: 'primary.dark', fontWeight: 800 }}>—</Box>
        <Typography variant="h3">{title}</Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 520 }}>{description}</Typography>
        {action}
      </Stack>
    </Paper>
  )
}
