import { Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { formatDateTime } from '../../utils/format'
import { listMedicalHistory, medicalRecordKeys } from './api'

export function PatientMedicalHistoryPage() {
  const query = useQuery({ queryKey: medicalRecordKeys.history, queryFn: listMedicalHistory })
  return (
    <>
      <PageHeader eyebrow="Patient · Chỉ đọc" title="Lịch sử khám" description="Chỉ hồ sơ gắn với lịch hẹn của chính bạn được Backend trả về." />
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? <EmptyState title="Chưa có hồ sơ khám" description="Hồ sơ sẽ xuất hiện sau khi bác sĩ hoàn tất lịch khám và lập kết quả." /> : (
        <Stack spacing={2}>
          {query.data.map((record) => (
            <Card key={record.id}><CardContent><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}>
              <Stack spacing={0.75}><Typography variant="h3">Kết quả khám</Typography><Typography color="text.secondary">Cập nhật {formatDateTime(record.updated_at)}</Typography><Typography><strong>Kết luận:</strong> {record.doctor_conclusion}</Typography></Stack>
              <Button component={RouterLink} to={`/medical-history/${record.id}`} variant="outlined" sx={{ alignSelf: { xs: 'stretch', sm: 'center' } }}>Xem chi tiết</Button>
            </Stack></CardContent></Card>
          ))}
        </Stack>
      )}
    </>
  )
}
