import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import { formatDateTime } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'
import { createHandoff, handoffKeys, listHandoffs, updateHandoff } from './api'
import { useHandoffRealtime } from './useHandoffRealtime'

const schema = z.object({ reason: z.string().trim().min(2).max(5000), priority: z.enum(['NORMAL', 'HIGH', 'URGENT']) })
type Values = z.infer<typeof schema>

export function HandoffPage() {
  const { user } = useAuth()
  const canHandle = user?.roles.some((role) => role === 'STAFF' || role === 'ADMIN') ?? false
  const realtime = useHandoffRealtime(canHandle)
  const client = useQueryClient()
  const query = useQuery({ queryKey: handoffKeys.all, queryFn: listHandoffs })
  const [open, setOpen] = useState(false)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { reason: '', priority: 'NORMAL' } })
  const invalidate = () => client.invalidateQueries({ queryKey: handoffKeys.all })
  const create = useMutation({ mutationFn: (values: Values) => createHandoff({ ...values, source: 'USER' }), onSuccess: async () => { setOpen(false); form.reset(); await invalidate() } })
  const update = useMutation({ mutationFn: ({ id, status }: { id: string; status: 'IN_PROGRESS' | 'RESOLVED' }) => updateHandoff(id, { status }), onSuccess: invalidate })
  return (
    <>
      <PageHeader eyebrow={canHandle ? 'Staff / Admin' : 'Hỗ trợ người dùng'} title="Yêu cầu chuyển nhân viên" description="PostgreSQL là nguồn dữ liệu chính; WebSocket chỉ đồng bộ notification và trạng thái gần thời gian thực." action={<Button variant="contained" onClick={() => setOpen(true)}>Tạo yêu cầu</Button>} />
      {canHandle && <Alert severity={realtime === 'connected' ? 'success' : realtime === 'error' ? 'error' : 'warning'}>
        {realtime === 'connected' ? 'Đã kết nối cập nhật thời gian thực.' : 'Đang kết nối lại; danh sách REST vẫn là nguồn dữ liệu chính.'}
      </Alert>}
      {(create.isError || update.isError) && <ErrorState error={create.error ?? update.error} />}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data.length === 0 ? <EmptyState title="Chưa có yêu cầu hỗ trợ" description="Yêu cầu mới sẽ xuất hiện tại đây." /> : <Stack spacing={2}>{query.data.map((item) => <Card key={item.id}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}><Stack spacing={1}><Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><StatusChip value={item.status} /><StatusChip value={item.priority} /></Stack><Typography variant="h3">{item.reason}</Typography><Typography color="text.secondary">Tạo {formatDateTime(item.created_at)} · nguồn {item.source}</Typography>{item.assigned_to && <Typography variant="body2">Người xử lý: {item.assigned_to}</Typography>}</Stack>{canHandle && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignSelf: { md: 'center' } }}>{item.status === 'PENDING' && <Button variant="contained" onClick={() => update.mutate({ id: item.id, status: 'IN_PROGRESS' })}>Tiếp nhận</Button>}{item.status === 'IN_PROGRESS' && <Button variant="contained" color="success" onClick={() => update.mutate({ id: item.id, status: 'RESOLVED' })}>Hoàn tất</Button>}</Stack>}</Stack></CardContent></Card>)}</Stack>}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm"><form onSubmit={form.handleSubmit((values) => create.mutate(values))}><DialogTitle>Tạo yêu cầu hỗ trợ</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{!canHandle && <Alert severity="info">Backend sẽ chuẩn hóa priority của người dùng về NORMAL.</Alert>}<TextField label="Lý do cần nhân viên hỗ trợ" multiline minRows={4} {...form.register('reason')} error={Boolean(form.formState.errors.reason)} helperText={form.formState.errors.reason?.message} /><TextField select label="Mức ưu tiên" defaultValue="NORMAL" disabled={!canHandle} {...form.register('priority')}><MenuItem value="NORMAL">Bình thường</MenuItem><MenuItem value="HIGH">Cao</MenuItem><MenuItem value="URGENT">Khẩn</MenuItem></TextField>{create.isError && <ErrorState error={create.error} />}</Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)}>Đóng</Button><Button type="submit" variant="contained" disabled={create.isPending}>Tạo yêu cầu</Button></DialogActions></form></Dialog>
    </>
  )
}
