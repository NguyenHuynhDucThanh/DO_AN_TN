import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Link, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link as RouterLink, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { parseApiError } from '../../api/errors'
import { useAuth } from './AuthContext'

const schema = z.object({
  email: z.string().trim().email('Email không hợp lệ.'),
  password: z.string().min(1, 'Vui lòng nhập mật khẩu.'),
})
type Values = z.infer<typeof schema>

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } })
  if (status === 'authenticated') return <Navigate to="/" replace />
  const submit = async (values: Values) => {
    setError(null)
    try {
      await login(values)
      const requested = (location.state as { from?: string } | null)?.from
      navigate(requested?.startsWith('/') ? requested : '/', { replace: true })
    } catch (requestError) {
      setError(parseApiError(requestError).message)
    }
  }
  return (
    <Card sx={{ maxWidth: 520, mx: 'auto' }}>
      <CardContent sx={{ p: { xs: 3, sm: 5 } }}>
        <Stack component="form" spacing={2.5} onSubmit={form.handleSubmit(submit)}>
          <Stack spacing={0.75}>
            <Typography variant="overline" color="primary">Tài khoản</Typography>
            <Typography variant="h2">Đăng nhập</Typography>
            <Typography color="text.secondary">Phiên đăng nhập được bảo vệ bằng HttpOnly cookie; token không được lưu trong trình duyệt bằng JavaScript.</Typography>
          </Stack>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField label="Email" type="email" autoComplete="email" {...form.register('email')} error={Boolean(form.formState.errors.email)} helperText={form.formState.errors.email?.message} />
          <TextField label="Mật khẩu" type="password" autoComplete="current-password" {...form.register('password')} error={Boolean(form.formState.errors.password)} helperText={form.formState.errors.password?.message} />
          <Button type="submit" variant="contained" size="large" disabled={form.formState.isSubmitting}>Đăng nhập</Button>
          <Typography color="text.secondary">Chưa có tài khoản Patient? <Link component={RouterLink} to="/register">Đăng ký</Link></Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}
