import { Alert, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import { formatDateTime } from '../../utils/format'
import { appointmentKeys, listAppointments, setAppointmentOutcome } from './api'

export function DoctorAppointmentsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: appointmentKeys.all, queryFn: listAppointments })
  const outcome = useMutation({ mutationFn: ({ id, status }: { id: string; status: 'COMPLETED' | 'NO_SHOW' }) => setAppointmentOutcome(id, status), onSuccess: () => queryClient.invalidateQueries({ queryKey: appointmentKeys.all }) })
  return (
    <>
      <PageHeader eyebrow="Doctor" title="Lịch hẹn được phân công" description="Backend quyết định ownership và chỉ cho chuyển CONFIRMED sang COMPLETED hoặc NO_SHOW." />
      {outcome.isError && <ErrorState error={outcome.error} />}
      {outcome.isSuccess && <Alert severity="success" sx={{ mb: 2 }}>Đã cập nhật kết quả lịch hẹn.</Alert>}
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? <EmptyState title="Không có lịch hẹn" description="Chưa có Appointment nào được phân công cho bác sĩ này." /> : (
        <Stack spacing={2}>{query.data.map((appointment) => <Card key={appointment.id}><CardContent><Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}><Stack spacing={0.75}><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><Typography variant="h3">Appointment</Typography><StatusChip value={appointment.status} /></Stack><Typography color="text.secondary">Đặt lúc {formatDateTime(appointment.booked_at)}</Typography><Typography variant="body2">Patient: {appointment.patient_id}</Typography><Typography variant="body2">Slot: {appointment.schedule_slot_id}</Typography></Stack><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: 'center' }}>{appointment.status === 'CONFIRMED' && <><Button variant="contained" onClick={() => outcome.mutate({ id: appointment.id, status: 'COMPLETED' })}>Đã khám</Button><Button variant="outlined" color="error" onClick={() => outcome.mutate({ id: appointment.id, status: 'NO_SHOW' })}>Không đến</Button></>}{appointment.status === 'COMPLETED' && <Button component={RouterLink} to={`/doctor/appointments/${appointment.id}/medical-record`} variant="outlined">Hồ sơ khám</Button>}</Stack></Stack></CardContent></Card>)}</Stack>
      )}
    </>
  )
}
