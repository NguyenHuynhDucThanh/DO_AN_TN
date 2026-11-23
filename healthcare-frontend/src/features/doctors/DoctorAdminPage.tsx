import { zodResolver } from '@hookform/resolvers/zod'
import {
  Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControlLabel, MenuItem, Stack, Switch, TextField, Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import type { Doctor } from '../../types/domain'
import { listSpecialties, specialtyKeys } from '../specialties/api'
import {
  createDoctor, doctorKeys, listDoctorCandidates, listDoctors, provisionDoctor, updateDoctor,
} from './api'

const schema = z.object({
  account_mode: z.enum(['NEW', 'EXISTING']),
  user_id: z.string(), email: z.string(), password: z.string(), confirm_password: z.string(),
  full_name: z.string(), phone: z.string(), specialty_id: z.string().uuid('Chuyên khoa không hợp lệ.'),
  license_number: z.string().trim().min(2).max(50), biography: z.string().max(5000), is_active: z.boolean(),
}).superRefine((values, context) => {
  if (values.account_mode === 'EXISTING') {
    if (!z.string().uuid().safeParse(values.user_id).success) context.addIssue({ code: 'custom', path: ['user_id'], message: 'Hãy chọn một tài khoản bác sĩ.' })
    return
  }
  if (!z.string().email().safeParse(values.email.trim()).success) context.addIssue({ code: 'custom', path: ['email'], message: 'Email không hợp lệ.' })
  if (values.full_name.trim().length < 2) context.addIssue({ code: 'custom', path: ['full_name'], message: 'Họ tên phải có ít nhất 2 ký tự.' })
  if (values.phone.trim().length < 8) context.addIssue({ code: 'custom', path: ['phone'], message: 'Số điện thoại phải có ít nhất 8 ký tự.' })
  if (values.password.length < 8 || !/[A-Za-z]/.test(values.password) || !/\d/.test(values.password)) context.addIssue({ code: 'custom', path: ['password'], message: 'Mật khẩu cần ít nhất 8 ký tự, gồm chữ và số.' })
  if (values.confirm_password !== values.password) context.addIssue({ code: 'custom', path: ['confirm_password'], message: 'Mật khẩu xác nhận không khớp.' })
})
type Values = z.infer<typeof schema>

const emptyValues: Values = {
  account_mode: 'NEW', user_id: '', email: '', password: '', confirm_password: '', full_name: '', phone: '',
  specialty_id: '', license_number: '', biography: '', is_active: true,
}

export function DoctorAdminPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: doctorKeys.all, queryFn: () => listDoctors() })
  const specialties = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties(true) })
  const [editing, setEditing] = useState<Doctor | 'new' | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: emptyValues })
  const accountMode = useWatch({ control: form.control, name: 'account_mode' })
  const candidates = useQuery({ queryKey: doctorKeys.candidates, queryFn: listDoctorCandidates, enabled: editing === 'new' })

  useEffect(() => {
    if (editing && editing !== 'new') form.reset({ ...emptyValues, account_mode: 'EXISTING', user_id: editing.user_id, specialty_id: editing.specialty_id, license_number: editing.license_number, biography: editing.biography ?? '', is_active: editing.is_active })
    else if (editing === 'new') form.reset(emptyValues)
  }, [editing, form])

  const save = useMutation({
    mutationFn: (values: Values) => {
      if (editing !== 'new') return updateDoctor((editing as Doctor).id, { specialty_id: values.specialty_id, license_number: values.license_number, biography: values.biography, is_active: values.is_active })
      if (values.account_mode === 'EXISTING') return createDoctor({ user_id: values.user_id, specialty_id: values.specialty_id, license_number: values.license_number, biography: values.biography })
      return provisionDoctor({ email: values.email.trim(), password: values.password, full_name: values.full_name.trim(), phone: values.phone.trim(), specialty_id: values.specialty_id, license_number: values.license_number, biography: values.biography })
    },
    onSuccess: async () => {
      setEditing(null)
      await Promise.all([client.invalidateQueries({ queryKey: doctorKeys.all }), client.invalidateQueries({ queryKey: doctorKeys.candidates })])
    },
  })

  const isCreating = editing === 'new'
  return (
    <>
      <PageHeader eyebrow="Quản trị" title="Quản lý bác sĩ" description="Tạo tài khoản, lập hồ sơ bác sĩ hoặc liên kết một tài khoản bác sĩ có sẵn." action={<Button variant="contained" onClick={() => setEditing('new')}>Thêm bác sĩ</Button>} />
      {save.isError && <ErrorState error={save.error} />}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data.length === 0 ? <EmptyState title="Chưa có bác sĩ" description="Bấm Thêm bác sĩ để tạo tài khoản và hồ sơ bác sĩ." /> : (
        <Stack spacing={1.25}>{query.data.map((item) => <Card key={item.id}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { md: 'center' } }}><Stack spacing={0.5}><Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}><Typography variant="h3">{item.user.full_name}</Typography><StatusChip value={item.is_active ? 'ACTIVE' : 'INACTIVE'} /></Stack><Typography color="primary.dark" sx={{ fontWeight: 650 }}>{item.specialty.name}</Typography><Typography variant="body2" color="text.secondary">Giấy phép hành nghề: {item.license_number}</Typography></Stack><Button variant="outlined" onClick={() => setEditing(item)}>Chỉnh sửa</Button></Stack></CardContent></Card>)}</Stack>
      )}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="md">
        <form onSubmit={form.handleSubmit((values) => save.mutate(values))}>
          <DialogTitle>{isCreating ? 'Thêm bác sĩ' : 'Cập nhật bác sĩ'}</DialogTitle>
          <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
            {isCreating && <><Typography variant="h4">Thông tin tài khoản</Typography><Controller name="account_mode" control={form.control} render={({ field }) => <TextField select label="Tài khoản" {...field}><MenuItem value="NEW">Tạo tài khoản bác sĩ mới</MenuItem><MenuItem value="EXISTING">Dùng tài khoản bác sĩ có sẵn</MenuItem></TextField>} /></>}
            {isCreating && accountMode === 'NEW' && <><TextField label="Họ và tên" {...form.register('full_name')} error={Boolean(form.formState.errors.full_name)} helperText={form.formState.errors.full_name?.message} /><TextField label="Email" type="email" {...form.register('email')} error={Boolean(form.formState.errors.email)} helperText={form.formState.errors.email?.message} /><TextField label="Số điện thoại" {...form.register('phone')} error={Boolean(form.formState.errors.phone)} helperText={form.formState.errors.phone?.message} /><TextField label="Mật khẩu tạm thời" type="password" autoComplete="new-password" {...form.register('password')} error={Boolean(form.formState.errors.password)} helperText={form.formState.errors.password?.message} /><TextField label="Xác nhận mật khẩu" type="password" autoComplete="new-password" {...form.register('confirm_password')} error={Boolean(form.formState.errors.confirm_password)} helperText={form.formState.errors.confirm_password?.message} /></>}
            {isCreating && accountMode === 'EXISTING' && <>{candidates.isError && <ErrorState error={candidates.error} onRetry={() => void candidates.refetch()} />}{candidates.data?.length === 0 && <Alert severity="info">Không có tài khoản bác sĩ nào chưa được gắn hồ sơ.</Alert>}<Controller name="user_id" control={form.control} render={({ field }) => <TextField select label="Tài khoản bác sĩ" disabled={candidates.isPending || candidates.isError || candidates.data?.length === 0} {...field} error={Boolean(form.formState.errors.user_id)} helperText={candidates.isPending ? 'Đang tải tài khoản…' : form.formState.errors.user_id?.message}>{(candidates.data ?? []).map((item) => <MenuItem key={item.id} value={item.id}>{item.full_name} — {item.email}</MenuItem>)}</TextField>} /></>}
            <Typography variant="h4" sx={{ pt: 1 }}>Hồ sơ chuyên môn</Typography>
            <Controller name="specialty_id" control={form.control} render={({ field }) => <TextField select label="Chuyên khoa" {...field} error={Boolean(form.formState.errors.specialty_id)} helperText={form.formState.errors.specialty_id?.message}>{(specialties.data ?? []).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>} />
            <TextField label="Số giấy phép" {...form.register('license_number')} error={Boolean(form.formState.errors.license_number)} helperText={form.formState.errors.license_number?.message} />
            <TextField label="Giới thiệu" multiline minRows={3} {...form.register('biography')} />
            {!isCreating && <Controller name="is_active" control={form.control} render={({ field }) => <FormControlLabel control={<Switch checked={field.value} onChange={(_, checked) => field.onChange(checked)} />} label="Đang hoạt động" />} />}
          </Stack></DialogContent>
          <DialogActions><Button onClick={() => setEditing(null)}>Hủy</Button><Button type="submit" variant="contained" disabled={save.isPending}>{save.isPending ? 'Đang lưu…' : 'Lưu'}</Button></DialogActions>
        </form>
      </Dialog>
    </>
  )
}
