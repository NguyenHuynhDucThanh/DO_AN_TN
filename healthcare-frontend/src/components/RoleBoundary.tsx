import { Alert, Button, Stack } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import type { Role } from '../types/domain'

export function RoleBoundary({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth()
  if (user?.roles.some((role) => roles.includes(role))) return children
  return (
    <Stack spacing={2}>
      <Alert severity="warning">Tài khoản hiện tại không có quyền truy cập màn hình này. Backend vẫn là nơi quyết định quyền cuối cùng.</Alert>
      <Button component={RouterLink} to="/" variant="outlined" sx={{ alignSelf: 'flex-start' }}>Về trang chủ</Button>
    </Stack>
  )
}
