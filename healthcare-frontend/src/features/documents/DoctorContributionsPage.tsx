import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import type { DocumentContribution } from '../../types/domain'
import { formatDateTime } from '../../utils/format'
import { documentKeys, listOwnContributions, updateContribution, uploadContribution } from './api'
import { approvalLabels, ingestionLabels } from './status'

const metadataSchema = z.object({
  title: z.string().trim().min(2, 'Tiêu đề phải có ít nhất 2 ký tự.').max(255),
  source_name: z.string().trim().max(255),
  source_url: z.union([z.literal(''), z.string().url('URL nguồn không hợp lệ.').max(1000)]),
  author_name: z.string().trim().max(255),
  organization: z.string().trim().max(255),
  publication_year: z.union([z.literal(''), z.string().regex(/^\d{4}$/, 'Năm xuất bản phải gồm 4 chữ số.')]),
})
type MetadataValues = z.infer<typeof metadataSchema>

const emptyValues: MetadataValues = { title: '', source_name: '', source_url: '', author_name: '', organization: '', publication_year: '' }
const allowedExtensions = ['.pdf', '.docx', '.csv', '.json', '.jsonl']

function payload(values: MetadataValues) {
  return {
    title: values.title,
    source_name: values.source_name || undefined,
    source_url: values.source_url || undefined,
    author_name: values.author_name || undefined,
    organization: values.organization || undefined,
    publication_year: values.publication_year ? Number(values.publication_year) : undefined,
  }
}

function MetadataFields({ form }: { form: ReturnType<typeof useForm<MetadataValues>> }) {
  const errors = form.formState.errors
  return <Stack spacing={2} sx={{ pt: 1 }}>
    <TextField label="Tiêu đề" required {...form.register('title')} error={Boolean(errors.title)} helperText={errors.title?.message} />
    <TextField label="Nguồn" {...form.register('source_name')} />
    <TextField label="URL nguồn" {...form.register('source_url')} error={Boolean(errors.source_url)} helperText={errors.source_url?.message} />
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Tác giả" {...form.register('author_name')} /></Grid>
      <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Tổ chức" {...form.register('organization')} /></Grid>
    </Grid>
    <TextField label="Năm xuất bản" inputMode="numeric" {...form.register('publication_year')} error={Boolean(errors.publication_year)} helperText={errors.publication_year?.message} />
  </Stack>
}

function UploadDialog({ onClose }: { onClose: () => void }) {
  const client = useQueryClient()
  const form = useForm<MetadataValues>({ resolver: zodResolver(metadataSchema), defaultValues: emptyValues })
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const upload = useMutation({
    mutationFn: (values: MetadataValues) => {
      if (!file) throw new Error('missing_file')
      return uploadContribution(file, payload(values))
    },
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: documentKeys.contributions }),
        client.invalidateQueries({ queryKey: documentKeys.all }),
      ])
      onClose()
    },
  })
  const submit = form.handleSubmit((values) => {
    if (!file) { setFileError('Hãy chọn một tệp tài liệu.'); return }
    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!allowedExtensions.includes(extension)) { setFileError('Chỉ hỗ trợ PDF, DOCX, CSV, JSON và JSONL.'); return }
    if (file.size > 25_000_000) { setFileError('Tệp vượt quá giới hạn 25 MB.'); return }
    setFileError('')
    upload.mutate(values)
  })
  return <Dialog open onClose={upload.isPending ? undefined : onClose} fullWidth maxWidth="sm">
    <form onSubmit={submit}>
      <DialogTitle>Đóng góp tài liệu</DialogTitle>
      <DialogContent><Stack spacing={2}>
        <Alert severity="info">Hỗ trợ PDF, DOCX, CSV, JSON, JSONL; dung lượng tối đa 25 MB. Tài liệu cần được quản trị viên duyệt trước khi đưa vào kho tri thức.</Alert>
        {upload.isError && <ErrorState error={upload.error} />}
        <Button component="label" variant="outlined">
          Chọn tệp
          <input hidden type="file" accept=".pdf,.docx,.csv,.json,.jsonl" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setFileError('') }} />
        </Button>
        <Typography variant="body2" color="text.secondary">{file ? `Đã chọn: ${file.name}` : 'Chưa chọn tệp'}</Typography>
        {fileError && <Alert severity="error">{fileError}</Alert>}
        <MetadataFields form={form} />
      </Stack></DialogContent>
      <DialogActions><Button onClick={onClose} disabled={upload.isPending}>Hủy</Button><Button type="submit" variant="contained" disabled={upload.isPending}>{upload.isPending ? 'Đang tải lên…' : 'Gửi tài liệu'}</Button></DialogActions>
    </form>
  </Dialog>
}

function EditDialog({ document, onClose }: { document: DocumentContribution; onClose: () => void }) {
  const client = useQueryClient()
  const form = useForm<MetadataValues>({ resolver: zodResolver(metadataSchema), defaultValues: emptyValues })
  useEffect(() => {
    form.reset({
      title: document.title,
      source_name: document.source_name ?? '',
      source_url: document.source_url ?? '',
      author_name: document.author_name ?? '',
      organization: document.organization ?? '',
      publication_year: document.publication_year ? String(document.publication_year) : '',
    })
  }, [document, form])
  const update = useMutation({
    mutationFn: (values: MetadataValues) => updateContribution(document.id, payload(values)),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: documentKeys.contributions }),
        client.invalidateQueries({ queryKey: documentKeys.all }),
      ])
      onClose()
    },
  })
  return <Dialog open onClose={update.isPending ? undefined : onClose} fullWidth maxWidth="sm"><form onSubmit={form.handleSubmit((values) => update.mutate(values))}>
    <DialogTitle>{document.approval_status === 'REJECTED' ? 'Chỉnh sửa và gửi lại' : 'Chỉnh sửa thông tin'}</DialogTitle>
    <DialogContent><Stack spacing={2}>{document.rejection_reason && <Alert severity="warning">Lý do từ chối: {document.rejection_reason}</Alert>}{update.isError && <ErrorState error={update.error} />}<MetadataFields form={form} /></Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={update.isPending}>Hủy</Button><Button type="submit" variant="contained" disabled={update.isPending}>{update.isPending ? 'Đang lưu…' : document.approval_status === 'REJECTED' ? 'Gửi lại' : 'Lưu'}</Button></DialogActions>
  </form></Dialog>
}

export function DoctorContributionsPage() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [editing, setEditing] = useState<DocumentContribution | null>(null)
  const query = useQuery({ queryKey: documentKeys.contributions, queryFn: listOwnContributions })
  return <>
    <PageHeader eyebrow="Dành cho bác sĩ" title="Tài liệu đóng góp" description="Gửi tài liệu y khoa để quản trị viên kiểm duyệt trước khi dùng làm nguồn tra cứu." action={<Button variant="contained" onClick={() => setUploadOpen(true)}>Đóng góp tài liệu</Button>} />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? <EmptyState title="Chưa có tài liệu đóng góp" description="Bấm Đóng góp tài liệu để gửi nguồn tri thức y khoa đầu tiên." /> : <Grid container spacing={2}>{query.data.map((item) => <Grid key={item.id} size={{ xs: 12, lg: 6 }}><Card><CardContent><Stack spacing={1.25}>
      <Typography variant="h3">{item.title}</Typography>
      <Typography color="text.secondary">{item.file_name} · {item.file_type}</Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><StatusChip value={item.approval_status} label={approvalLabels[item.approval_status]} /><StatusChip value={item.ingestion_status} label={ingestionLabels[item.ingestion_status]} /></Stack>
      <Typography variant="body2">Nguồn: {item.source_name || item.source_url || 'Chưa khai báo'}</Typography>
      {(item.author_name || item.organization) && <Typography variant="body2">{[item.author_name, item.organization].filter(Boolean).join(' · ')}</Typography>}
      {item.publication_year && <Typography variant="body2">Năm xuất bản: {item.publication_year}</Typography>}
      <Typography variant="body2">Ngày gửi: {formatDateTime(item.created_at)}</Typography>
      {item.rejection_reason && <Alert severity="warning">Lý do từ chối: {item.rejection_reason}</Alert>}
      {['PENDING', 'REJECTED'].includes(item.approval_status) && <Button variant="outlined" size="small" sx={{ alignSelf: 'flex-start' }} onClick={() => setEditing(item)}>{item.approval_status === 'REJECTED' ? 'Chỉnh sửa và gửi lại' : 'Chỉnh sửa thông tin'}</Button>}
    </Stack></CardContent></Card></Grid>)}</Grid>}
    {uploadOpen && <UploadDialog onClose={() => setUploadOpen(false)} />}
    {editing && <EditDialog document={editing} onClose={() => setEditing(null)} />}
  </>
}
