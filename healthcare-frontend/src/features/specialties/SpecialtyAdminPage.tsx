import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Switch, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import type { Specialty } from '../../types/domain'
import { createSpecialty, listSpecialties, setSpecialtyStatus, specialtyKeys, updateSpecialty } from './api'

const schema = z.object({ code: z.string().trim().min(2).max(30), name: z.string().trim().min(2).max(120), description: z.string().max(4000) })
type Values = z.infer<typeof schema>

export function SpecialtyAdminPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties() })
  const [editing, setEditing] = useState<Specialty | 'new' | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { code: '', name: '', description: '' } })
  useEffect(() => { if (editing && editing !== 'new') form.reset({ code: editing.code, name: editing.name, description: editing.description ?? '' }); else if (editing === 'new') form.reset({ code: '', name: '', description: '' }) }, [editing, form])
  const invalidate = () => client.invalidateQueries({ queryKey: specialtyKeys.all })
  const save = useMutation({ mutationFn: (values: Values) => editing === 'new' ? createSpecialty(values) : updateSpecialty((editing as Specialty).id, { name: values.name, description: values.description }), onSuccess: async () => { setEditing(null); await invalidate() } })
  const toggle = useMutation({ mutationFn: ({ id, active }: { id: string; active: boolean }) => setSpecialtyStatus(id, active), onSuccess: invalidate })
  return (
    <>
      <PageHeader eyebrow="Admin" title="Quản lý chuyên khoa" description="Master data chỉ được thay đổi bởi Admin; Backend tiếp tục kiểm tra quyền." action={<Button variant="contained" onClick={() => setEditing('new')}>Thêm chuyên khoa</Button>} />
      {(save.isError || toggle.isError) && <ErrorState error={save.error ?? toggle.error} />}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data.length === 0 ? <EmptyState title="Chưa có chuyên khoa" description="Tạo chuyên khoa đầu tiên để bắt đầu." /> : <Stack spacing={1.5}>{query.data.map((item) => <Card key={item.id}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}><Stack><Typography variant="h3">{item.name}</Typography><Typography color="text.secondary">{item.code} · {item.description || 'Chưa có mô tả'}</Typography></Stack><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><Typography variant="body2">{item.is_active ? 'Đang hoạt động' : 'Đã tắt'}</Typography><Switch checked={item.is_active} onChange={(_, checked) => toggle.mutate({ id: item.id, active: checked })} /><Button onClick={() => setEditing(item)}>Chỉnh sửa</Button></Stack></Stack></CardContent></Card>)}</Stack>}
      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm"><form onSubmit={form.handleSubmit((values) => save.mutate(values))}><DialogTitle>{editing === 'new' ? 'Thêm chuyên khoa' : 'Cập nhật chuyên khoa'}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="Mã chuyên khoa" disabled={editing !== 'new'} {...form.register('code')} error={Boolean(form.formState.errors.code)} helperText={form.formState.errors.code?.message} /><TextField label="Tên chuyên khoa" {...form.register('name')} error={Boolean(form.formState.errors.name)} helperText={form.formState.errors.name?.message} /><TextField label="Mô tả" multiline minRows={3} {...form.register('description')} />{save.isError && <Alert severity="error">Không thể lưu chuyên khoa.</Alert>}</Stack></DialogContent><DialogActions><Button onClick={() => setEditing(null)}>Đóng</Button><Button type="submit" variant="contained" disabled={save.isPending}>Lưu</Button></DialogActions></form></Dialog>
    </>
  )
}
