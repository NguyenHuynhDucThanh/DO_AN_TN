import { Alert, Card, CardContent, Grid, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import { formatDateTime } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'
import { doctorKeys, listDoctors } from '../doctors/api'
import { listAvailableSlots, listSchedules, scheduleKeys } from './api'
import type { Schedule } from '../../types/domain'

function AvailableSlots({ schedule }: { schedule: Schedule }) {
  const filters = { from_at: schedule.start_at, to_at: schedule.end_at, doctor_id: schedule.doctor_id }
  const query = useQuery({ queryKey: scheduleKeys.available(filters), queryFn: () => listAvailableSlots(filters) })
  if (query.isPending) return <LoadingState label="Đang tải slot…" />
  if (query.isError) return <ErrorState error={query.error} />
  if (!query.data.length) return <Typography color="text.secondary">Không còn slot AVAILABLE trong lịch này.</Typography>
  return <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>{query.data.map((slot) => <Card key={slot.id} variant="outlined"><CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}><Typography sx={{ fontWeight: 650 }}>{formatDateTime(slot.start_at)}</Typography></CardContent></Card>)}</Stack>
}

export function DoctorSchedulesPage() {
  const { user } = useAuth()
  const doctors = useQuery({ queryKey: doctorKeys.all, queryFn: () => listDoctors(undefined, true) })
  const doctor = doctors.data?.find((item) => item.user_id === user?.id)
  const schedules = useQuery({ queryKey: scheduleKeys.byDoctor(doctor?.id ?? ''), queryFn: () => listSchedules(doctor?.id), enabled: Boolean(doctor) })
  return (
    <>
      <PageHeader eyebrow="Doctor" title="Lịch làm việc" description="Hiển thị lịch của bác sĩ đang đăng nhập và các slot còn khả dụng." />
      {!user && <Alert severity="warning">Vui lòng đăng nhập bằng tài khoản Doctor.</Alert>}
      {doctors.isPending || (doctor && schedules.isPending) ? <LoadingState /> : doctors.isError ? <ErrorState error={doctors.error} /> : !doctor ? <EmptyState title="Không tìm thấy hồ sơ bác sĩ" description="Tài khoản đang đăng nhập chưa liên kết với doctors.user_id đang hoạt động." /> : schedules.isError ? <ErrorState error={schedules.error} onRetry={() => void schedules.refetch()} /> : !schedules.data?.length ? <EmptyState title="Chưa có lịch làm việc" description="Lịch do Backend quản lý sẽ xuất hiện tại đây." /> : (
        <Grid container spacing={2}>{schedules.data.map((schedule) => <Grid key={schedule.id} size={{ xs: 12, lg: 6 }}><Card><CardContent><Stack spacing={2}><Stack direction="row" sx={{ justifyContent: 'space-between', gap: 2 }}><Typography variant="h3">{formatDateTime(schedule.start_at)}</Typography><StatusChip value={schedule.status} /></Stack><Typography color="text.secondary">Kết thúc {formatDateTime(schedule.end_at)} · {schedule.slot_duration_minutes} phút/slot</Typography><AvailableSlots schedule={schedule} /></Stack></CardContent></Card></Grid>)}</Grid>
      )}
    </>
  )
}
