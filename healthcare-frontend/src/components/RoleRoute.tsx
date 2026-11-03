import { Alert, Button, Stack } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import type { Role } from '../types/domain'
import { ProtectedRoute } from './ProtectedRoute'

function AuthorizedContent({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth()
  if (user && user.roles.some((role) => roles.includes(role))) return children
  return (
    <Stack spacing={2}>
      <Alert severity="warning">Tài khoản của bạn không có quyền truy cập màn hình này.</Alert>
      <Button component={RouterLink} to="/" variant="outlined" sx={{ alignSelf: 'flex-start' }}>Về trang chủ</Button>
    </Stack>
  )
}

export function RoleRoute({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  return <ProtectedRoute><AuthorizedContent roles={roles}>{children}</AuthorizedContent></ProtectedRoute>
}
