import { Alert, Card, CardContent, Divider, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { formatDateTime } from '../../utils/format'
import { getMedicalRecord, medicalRecordKeys } from './api'

export function MedicalRecordDetailPage() {
  const { recordId = '' } = useParams()
  const query = useQuery({ queryKey: medicalRecordKeys.detail(recordId), queryFn: () => getMedicalRecord(recordId), enabled: Boolean(recordId) })
  if (query.isPending) return <LoadingState />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  const record = query.data
  return (
    <>
      <PageHeader eyebrow="Hồ sơ khám · Chỉ đọc" title="Kết quả khám" description={`Cập nhật lần cuối ${formatDateTime(record.updated_at)}`} />
      <Alert severity="info" sx={{ mb: 2 }}>Đây là dữ liệu lâm sàng riêng tư. Giao diện Patient không cung cấp thao tác chỉnh sửa.</Alert>
      <Card><CardContent sx={{ p: { xs: 3, md: 5 } }}><Stack spacing={3} divider={<Divider flexItem />}>
        <Stack spacing={1}><Typography variant="overline" color="primary">Triệu chứng ghi nhận</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{record.symptoms}</Typography></Stack>
        <Stack spacing={1}><Typography variant="overline" color="primary">Ghi chú khám</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{record.clinical_notes}</Typography></Stack>
        <Stack spacing={1}><Typography variant="overline" color="primary">Kết luận của bác sĩ</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{record.doctor_conclusion}</Typography></Stack>
        <Stack spacing={1}><Typography variant="overline" color="primary">Hướng dẫn sau khám</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{record.follow_up_instructions}</Typography></Stack>
      </Stack></CardContent></Card>
    </>
  )
}
