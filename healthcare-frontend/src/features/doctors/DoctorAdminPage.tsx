import { zodResolver } from '@hookform/resolvers/zod'
import { Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Switch, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import type { Doctor } from '../../types/domain'
import { listSpecialties, specialtyKeys } from '../specialties/api'
import { createDoctor, doctorKeys, listDoctors, updateDoctor } from './api'

const schema = z.object({ user_id: z.string().uuid('UUID người dùng không hợp lệ.'), specialty_id: z.string().uuid(), license_number: z.string().trim().min(2).max(50), biography: z.string().max(5000), is_active: z.boolean() })
type Values = z.infer<typeof schema>

export function DoctorAdminPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: doctorKeys.all, queryFn: () => listDoctors() })
  const specialties = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties(true) })
  const [editing, setEditing] = useState<Doctor | 'new' | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { user_id: '', specialty_id: '', license_number: '', biography: '', is_active: true } })
  useEffect(() => { if (editing && editing !== 'new') form.reset({ user_id: editing.user_id, specialty_id: editing.specialty_id, license_number: editing.license_number, biography: editing.biography ?? '', is_active: editing.is_active }); else if (editing === 'new') form.reset({ user_id: '', specialty_id: '', license_number: '', biography: '', is_active: true }) }, [editing, form])
  const save = useMutation({ mutationFn: (values: Values) => editing === 'new' ? createDoctor(values) : updateDoctor((editing as Doctor).id, { specialty_id: values.specialty_id, license_number: values.license_number, biography: values.biography, is_active: values.is_active }), onSuccess: async () => { setEditing(null); await client.invalidateQueries({ queryKey: doctorKeys.all }) } })
  return (
    <>
      <PageHeader eyebrow="Admin" title="Quản lý bác sĩ" description="Tạo Doctor từ một User đã có role DOCTOR trong PostgreSQL." action={<Button variant="contained" onClick={() => setEditing('new')}>Thêm hồ sơ bác sĩ</Button>} />
      {save.isError && <ErrorState error={save.error} />}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data.length === 0 ? <EmptyState title="Chưa có bác sĩ" description="Hãy tạo User có role DOCTOR trước, sau đó thêm master data bác sĩ." /> : <Stack spacing={1.5}>{query.data.map((item) => <Card key={item.id}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}><Stack><Typography variant="h3">{item.user.full_name}</Typography><Typography color="primary">{item.specialty.name}</Typography><Typography color="text.secondary">{item.license_number} · {item.is_active ? 'Đang hoạt động' : 'Đã tắt'}</Typography></Stack><Button onClick={() => setEditing(item)}>Chỉnh sửa</Button></Stack></CardContent></Card>)}</Stack>}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm"><form onSubmit={form.handleSubmit((values) => save.mutate(values))}><DialogTitle>{editing === 'new' ? 'Thêm hồ sơ bác sĩ' : 'Cập nhật bác sĩ'}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="User UUID" disabled={editing !== 'new'} {...form.register('user_id')} error={Boolean(form.formState.errors.user_id)} helperText={form.formState.errors.user_id?.message} /><TextField select label="Chuyên khoa" defaultValue="" {...form.register('specialty_id')} error={Boolean(form.formState.errors.specialty_id)} helperText={form.formState.errors.specialty_id?.message}>{specialties.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField label="Số giấy phép" {...form.register('license_number')} error={Boolean(form.formState.errors.license_number)} helperText={form.formState.errors.license_number?.message} /><TextField label="Giới thiệu" multiline minRows={3} {...form.register('biography')} /><Controller name="is_active" control={form.control} render={({ field }) => <FormControlLabel control={<Switch checked={field.value} onChange={(_, checked) => field.onChange(checked)} />} label="Đang hoạt động" />} /></Stack></DialogContent><DialogActions><Button onClick={() => setEditing(null)}>Đóng</Button><Button type="submit" variant="contained" disabled={save.isPending}>Lưu</Button></DialogActions></form></Dialog>
    </>
  )
}
