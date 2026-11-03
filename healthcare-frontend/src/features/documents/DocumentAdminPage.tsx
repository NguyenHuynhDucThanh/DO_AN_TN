import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import { formatDateTime } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'
import { createDocument, documentKeys, listDocuments, reviewDocument } from './api'

const schema = z.object({ title: z.string().trim().min(2).max(255), file_name: z.string().trim().min(1).max(255), file_type: z.enum(['CSV', 'PDF', 'DOCX']), storage_key: z.string().trim().min(1).max(500), source_name: z.string().max(255), source_url: z.union([z.literal(''), z.string().url('URL nguồn không hợp lệ.')]), checksum_sha256: z.string().regex(/^[0-9a-fA-F]{64}$/, 'SHA-256 phải có đúng 64 ký tự hex.'), version_number: z.number().int().min(1) })
type Values = z.infer<typeof schema>

export function DocumentAdminPage() {
  const { user } = useAuth()
  const isAdmin = user?.roles.includes('ADMIN') ?? false
  const client = useQueryClient()
  const query = useQuery({ queryKey: documentKeys.all, queryFn: listDocuments })
  const [open, setOpen] = useState(false)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { title: '', file_name: '', file_type: 'PDF', storage_key: '', source_name: '', source_url: '', checksum_sha256: '', version_number: 1 } })
  const invalidate = () => client.invalidateQueries({ queryKey: documentKeys.all })
  const create = useMutation({ mutationFn: createDocument, onSuccess: async () => { form.reset(); setOpen(false); await invalidate() } })
  const review = useMutation({ mutationFn: ({ id, status }: { id: string; status: 'APPROVED' | 'REJECTED' }) => reviewDocument(id, status), onSuccess: invalidate })
  return (
    <>
      <PageHeader eyebrow="Staff / Admin" title="Tài liệu tri thức" description="Phase 4 chỉ quản lý metadata và phê duyệt. Chưa upload file hoặc ingest vào RAG." action={<Button variant="contained" onClick={() => setOpen(true)}>Đăng ký metadata</Button>} />
      {(create.isError || review.isError) && <ErrorState error={create.error ?? review.error} />}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data.length === 0 ? <EmptyState title="Chưa có tài liệu" description="Đăng ký metadata JSON, CSV, PDF hoặc DOCX để quản trị nguồn RAG." /> : <Grid container spacing={2}>{query.data.map((item) => <Grid key={item.id} size={{ xs: 12, lg: 6 }}><Card><CardContent><Stack spacing={1.5}><Stack direction="row" sx={{ justifyContent: 'space-between', gap: 2 }}><Typography variant="h3">{item.title}</Typography><StatusChip value={item.approval_status} /></Stack><Typography color="text.secondary">{item.file_name} · v{item.version_number} · {item.file_type}</Typography><Typography variant="body2">Nguồn: {item.source_name || item.source_url || 'Chưa khai báo'}</Typography><Typography variant="body2">Tạo {formatDateTime(item.created_at)}</Typography><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><StatusChip value={item.ingestion_status} />{isAdmin && item.approval_status === 'PENDING' && <><Button size="small" variant="contained" onClick={() => review.mutate({ id: item.id, status: 'APPROVED' })}>Duyệt</Button><Button size="small" color="error" onClick={() => review.mutate({ id: item.id, status: 'REJECTED' })}>Từ chối</Button></>}</Stack></Stack></CardContent></Card></Grid>)}</Grid>}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md"><form onSubmit={form.handleSubmit((values) => create.mutate(values))}><DialogTitle>Đăng ký metadata tài liệu</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><Alert severity="info">Không chọn file tại bước này. storage_key và checksum được đăng ký theo API Phase 3.</Alert><TextField label="Tiêu đề" {...form.register('title')} error={Boolean(form.formState.errors.title)} helperText={form.formState.errors.title?.message} /><Grid container spacing={2}><Grid size={{ xs: 12, sm: 8 }}><TextField fullWidth label="Tên file" {...form.register('file_name')} error={Boolean(form.formState.errors.file_name)} helperText={form.formState.errors.file_name?.message} /></Grid><Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth select label="Loại file" defaultValue="PDF" {...form.register('file_type')}><MenuItem value="PDF">PDF</MenuItem><MenuItem value="DOCX">DOCX</MenuItem><MenuItem value="CSV">CSV</MenuItem></TextField></Grid></Grid><TextField label="Storage key" {...form.register('storage_key')} error={Boolean(form.formState.errors.storage_key)} helperText={form.formState.errors.storage_key?.message} /><TextField label="SHA-256" {...form.register('checksum_sha256')} error={Boolean(form.formState.errors.checksum_sha256)} helperText={form.formState.errors.checksum_sha256?.message} /><Grid container spacing={2}><Grid size={{ xs: 12, sm: 8 }}><TextField fullWidth label="Tên nguồn" {...form.register('source_name')} /></Grid><Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth type="number" label="Phiên bản" {...form.register('version_number', { valueAsNumber: true })} /></Grid></Grid><TextField label="URL nguồn" {...form.register('source_url')} error={Boolean(form.formState.errors.source_url)} helperText={form.formState.errors.source_url?.message} />{create.isError && <ErrorState error={create.error} />}</Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)}>Đóng</Button><Button type="submit" variant="contained" disabled={create.isPending}>Đăng ký</Button></DialogActions></form></Dialog>
    </>
  )
}
