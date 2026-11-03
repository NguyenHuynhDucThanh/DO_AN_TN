import { Button, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

export function NotFoundPage() {
  return <Stack spacing={2} sx={{ alignItems: 'flex-start' }}><Typography variant="overline" color="primary">404</Typography><Typography variant="h2">Không tìm thấy trang</Typography><Typography color="text.secondary">Đường dẫn không tồn tại trong Frontend Phase 4.</Typography><Button component={RouterLink} to="/" variant="contained">Về trang chủ</Button></Stack>
}
