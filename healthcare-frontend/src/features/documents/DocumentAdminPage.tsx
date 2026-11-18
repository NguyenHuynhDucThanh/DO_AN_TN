import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import type { DocumentMetadata } from '../../types/domain'
import { formatDateTime } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'
import { documentKeys, downloadDocumentFile, ingestDocument, listDocuments, reviewDocument } from './api'
import { approvalLabels, ingestionLabels } from './status'

function RejectDialog({ document, onClose }: { document: DocumentMetadata; onClose: () => void }) {
  const client = useQueryClient()
  const [reason, setReason] = useState('')
  const [validation, setValidation] = useState('')
  const reject = useMutation({
    mutationFn: () => reviewDocument(document.id, 'REJECTED', reason.trim()),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: documentKeys.all }),
        client.invalidateQueries({ queryKey: documentKeys.contributions }),
      ])
      onClose()
    },
  })
  const submit = () => {
    if (!reason.trim()) { setValidation('Hãy nhập lý do từ chối.'); return }
    setValidation('')
    reject.mutate()
  }
  return <Dialog open onClose={reject.isPending ? undefined : onClose} fullWidth maxWidth="sm">
    <DialogTitle>Từ chối tài liệu</DialogTitle>
    <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
      <Typography>{document.title}</Typography>
      {reject.isError && <ErrorState error={reject.error} />}
      <TextField autoFocus multiline minRows={3} label="Lý do từ chối" value={reason} onChange={(event) => setReason(event.target.value)} error={Boolean(validation)} helperText={validation} />
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={reject.isPending}>Đóng</Button><Button color="error" variant="contained" onClick={submit} disabled={reject.isPending}>{reject.isPending ? 'Đang gửi…' : 'Xác nhận từ chối'}</Button></DialogActions>
  </Dialog>
}

function DocumentCard({ item, isAdmin, onReject }: { item: DocumentMetadata; isAdmin: boolean; onReject: (item: DocumentMetadata) => void }) {
  const client = useQueryClient()
  const refresh = () => Promise.all([
    client.invalidateQueries({ queryKey: documentKeys.all }),
    client.invalidateQueries({ queryKey: documentKeys.contributions }),
  ])
  const approve = useMutation({ mutationFn: () => reviewDocument(item.id, 'APPROVED'), onSuccess: refresh })
  const ingest = useMutation({ mutationFn: () => ingestDocument(item.id), onSuccess: refresh })
  const download = useMutation({ mutationFn: () => downloadDocumentFile(item.id, item.file_name) })
  const error = approve.error ?? ingest.error ?? download.error
  const canIngest = item.approval_status === 'APPROVED' && ['NOT_INGESTED', 'FAILED'].includes(item.ingestion_status)
  return <Card><CardContent><Stack spacing={1.5}>
    <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ justifyContent: 'space-between', gap: 1 }}>
      <Typography variant="h3">{item.title}</Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><StatusChip value={item.approval_status} label={approvalLabels[item.approval_status]} /><StatusChip value={item.ingestion_status} label={ingestionLabels[item.ingestion_status]} /></Stack>
    </Stack>
    <Typography color="text.secondary">{item.file_name} · {item.file_type}</Typography>
    <Typography variant="body2">Người gửi: {item.uploader_name} ({item.uploader_email})</Typography>
    <Typography variant="body2">Nguồn: {item.source_name || item.source_url || 'Chưa khai báo'}</Typography>
    {(item.author_name || item.organization) && <Typography variant="body2">Tác giả/Tổ chức: {[item.author_name, item.organization].filter(Boolean).join(' · ')}</Typography>}
    {item.publication_year && <Typography variant="body2">Năm xuất bản: {item.publication_year}</Typography>}
    <Typography variant="body2">Ngày gửi: {formatDateTime(item.created_at)}</Typography>
    {item.rejection_reason && <Alert severity="warning">Lý do từ chối: {item.rejection_reason}</Alert>}
    {item.ingestion_status === 'FAILED' && <Alert severity="error">Không thể đưa tài liệu vào kho tri thức. Quản trị viên có thể thử lại.</Alert>}
    {error && <ErrorState error={error} />}
    {isAdmin && <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
      <Button size="small" variant="outlined" onClick={() => download.mutate()} disabled={download.isPending}>{download.isPending ? 'Đang mở…' : 'Kiểm tra tệp'}</Button>
      {item.approval_status === 'PENDING' && <Button size="small" variant="contained" onClick={() => approve.mutate()} disabled={approve.isPending}>{approve.isPending ? 'Đang duyệt…' : 'Duyệt'}</Button>}
      {item.approval_status === 'PENDING' && <Button size="small" color="error" onClick={() => onReject(item)}>Từ chối</Button>}
      {canIngest && <Button size="small" variant="contained" color="secondary" onClick={() => ingest.mutate()} disabled={ingest.isPending}>{ingest.isPending ? 'Đang xử lý…' : item.ingestion_status === 'FAILED' ? 'Thử xử lý lại' : 'Đưa vào kho tri thức'}</Button>}
    </Stack>}
  </Stack></CardContent></Card>
}

export function DocumentAdminPage() {
  const { user } = useAuth()
  const isAdmin = user?.roles.includes('ADMIN') ?? false
  const query = useQuery({ queryKey: documentKeys.all, queryFn: listDocuments })
  const [rejecting, setRejecting] = useState<DocumentMetadata | null>(null)
  return <>
    <PageHeader eyebrow="Quản lý nội dung" title="Tài liệu tri thức" description="Kiểm tra, phê duyệt và đưa tài liệu phù hợp vào nguồn tra cứu của chatbot." />
    {!isAdmin && <Alert severity="info" sx={{ mb: 2 }}>Bạn có thể xem trạng thái tài liệu. Chỉ quản trị viên được kiểm duyệt và xử lý nguồn tri thức.</Alert>}
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? <EmptyState title="Chưa có tài liệu" description="Các tài liệu được gửi sẽ xuất hiện tại đây để kiểm duyệt." /> : <Grid container spacing={2}>{query.data.map((item) => <Grid key={item.id} size={{ xs: 12, lg: 6 }}><DocumentCard item={item} isAdmin={isAdmin} onReject={setRejecting} /></Grid>)}</Grid>}
    {rejecting && <RejectDialog document={rejecting} onClose={() => setRejecting(null)} />}
  </>
}
