import { Alert, Box, Button, CircularProgress, Stack, Typography } from '@mui/material'
import axios from 'axios'
import { useHealth } from '../hooks/useHealth'

export function HealthStatus() {
  const health = useHealth()
  const databaseNotReady = axios.isAxiosError(health.error) && health.error.response?.status === 503

  return (
    <Stack spacing={2} aria-live="polite">
      <Typography variant="h6" component="h2">Kết nối hệ thống</Typography>
      {health.isPending && (
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          <CircularProgress size={20} />
          <Typography>Đang kiểm tra kết nối...</Typography>
        </Box>
      )}
      {health.isError && (
        <Alert severity="error">
          {databaseNotReady
            ? 'Backend đã phản hồi nhưng PostgreSQL hoặc pgvector chưa sẵn sàng.'
            : 'Chưa kết nối được Backend. Hãy kiểm tra dịch vụ và cấu hình kết nối.'}
        </Alert>
      )}
      {health.data && !health.isError && (
        <>
          <Alert severity={health.data.status === 'ok' ? 'success' : 'warning'}>
            {health.data.status === 'ok'
              ? 'Kết nối thành công. Backend, PostgreSQL và pgvector đã sẵn sàng.'
              : 'Backend chưa sẵn sàng.'}
          </Alert>
          <Typography variant="body2" color="text.secondary">
            Ứng dụng: {health.data.application} · Môi trường: {health.data.environment}
          </Typography>
        </>
      )}
      <Box>
        <Button variant="outlined" onClick={() => void health.refetch()} disabled={health.isFetching}>
          Kiểm tra lại
        </Button>
      </Box>
    </Stack>
  )
}
