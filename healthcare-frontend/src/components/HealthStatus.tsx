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
            ? 'Hệ thống đang khởi động dữ liệu. Vui lòng thử lại sau ít phút.'
            : 'Chưa kết nối được hệ thống. Vui lòng thử lại.'}
        </Alert>
      )}
      {health.data && !health.isError && (
        <>
          <Alert severity={health.data.status === 'ok' ? 'success' : 'warning'}>
            {health.data.status === 'ok'
              ? 'Kết nối thành công. Hệ thống đã sẵn sàng.'
              : 'Hệ thống chưa sẵn sàng.'}
          </Alert>
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
