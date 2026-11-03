import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Grid, Link, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link as RouterLink, Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { parseApiError } from '../../api/errors'
import { useAuth } from './AuthContext'

const schema = z.object({
  email: z.string().trim().email('Email không hợp lệ.'),
  password: z.string().min(8, 'Mật khẩu cần ít nhất 8 ký tự.').max(128).regex(/[A-Za-zÀ-ỹ]/, 'Mật khẩu cần có chữ.').regex(/[0-9]/, 'Mật khẩu cần có số.'),
  full_name: z.string().trim().min(2, 'Họ tên cần ít nhất 2 ký tự.').max(150),
  phone: z.string().trim().min(8, 'Số điện thoại là bắt buộc.').max(20),
  date_of_birth: z.string(),
  gender: z.enum(['', 'FEMALE', 'MALE', 'OTHER', 'UNDISCLOSED']),
})
type Values = z.infer<typeof schema>

export function RegisterPage() {
  const { register, status } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '', full_name: '', phone: '', date_of_birth: '', gender: '' } })
  if (status === 'authenticated') return <Navigate to="/" replace />
  const submit = async (values: Values) => {
    setError(null)
    try {
      await register({
        ...values,
        date_of_birth: values.date_of_birth || null,
        gender: values.gender || null,
      })
      navigate('/', { replace: true })
    } catch (requestError) {
      setError(parseApiError(requestError).message)
    }
  }
  return (
    <Card sx={{ maxWidth: 760, mx: 'auto' }}>
      <CardContent sx={{ p: { xs: 3, sm: 5 } }}>
        <Stack component="form" spacing={2.5} onSubmit={form.handleSubmit(submit)}>
          <Stack spacing={0.75}>
            <Typography variant="overline" color="primary">Tài khoản Patient</Typography>
            <Typography variant="h2">Đăng ký</Typography>
            <Typography color="text.secondary">Chỉ thu thập dữ liệu định danh và liên hệ tối thiểu. Hồ sơ khám không được nhập tại đây.</Typography>
          </Stack>
          {error && <Alert severity="error">{error}</Alert>}
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Họ và tên" autoComplete="name" {...form.register('full_name')} error={Boolean(form.formState.errors.full_name)} helperText={form.formState.errors.full_name?.message} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Số điện thoại" autoComplete="tel" {...form.register('phone')} error={Boolean(form.formState.errors.phone)} helperText={form.formState.errors.phone?.message} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Email" type="email" autoComplete="email" {...form.register('email')} error={Boolean(form.formState.errors.email)} helperText={form.formState.errors.email?.message} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Mật khẩu" type="password" autoComplete="new-password" {...form.register('password')} error={Boolean(form.formState.errors.password)} helperText={form.formState.errors.password?.message ?? 'Tối thiểu 8 ký tự, có chữ và số.'} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Ngày sinh (tùy chọn)" type="date" slotProps={{ inputLabel: { shrink: true } }} {...form.register('date_of_birth')} /></Grid>
            <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth select label="Giới tính (tùy chọn)" defaultValue="" {...form.register('gender')}><MenuItem value="">Không khai báo</MenuItem><MenuItem value="FEMALE">Nữ</MenuItem><MenuItem value="MALE">Nam</MenuItem><MenuItem value="OTHER">Khác</MenuItem><MenuItem value="UNDISCLOSED">Không muốn công bố</MenuItem></TextField></Grid>
          </Grid>
          <Button type="submit" variant="contained" size="large" disabled={form.formState.isSubmitting}>Tạo tài khoản</Button>
          <Typography color="text.secondary">Đã có tài khoản? <Link component={RouterLink} to="/login">Đăng nhập</Link></Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}
