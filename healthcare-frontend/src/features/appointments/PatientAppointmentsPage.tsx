import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import { formatDateTime } from '../../utils/format'
import { appointmentKeys, cancelAppointment, listAppointments } from './api'

const cancelSchema = z.object({ reason: z.string().trim().min(2, 'Lý do phải có ít nhất 2 ký tự.').max(500) })
type CancelValues = z.infer<typeof cancelSchema>

export function PatientAppointmentsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: appointmentKeys.all, queryFn: listAppointments })
  const [cancelId, setCancelId] = useState<string | null>(null)
  const form = useForm<CancelValues>({ resolver: zodResolver(cancelSchema), defaultValues: { reason: '' } })
  const cancellation = useMutation({
    mutationFn: (values: CancelValues) => cancelAppointment(cancelId ?? '', values.reason),
    onSuccess: async () => { setCancelId(null); form.reset(); await queryClient.invalidateQueries({ queryKey: appointmentKeys.all }) },
  })
  return (
    <>
      <PageHeader eyebrow="Dành cho người bệnh" title="Lịch hẹn của tôi" description="Theo dõi lịch sắp tới và những lịch đã hủy." />
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? <EmptyState title="Bạn chưa có lịch hẹn" description="Tìm một khung giờ phù hợp để đặt lịch khám đầu tiên." /> : (
        <Stack spacing={2}>
          {query.data.map((appointment) => (
            <Card key={appointment.id}><CardContent><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between' }}>
              <Stack spacing={0.75}>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                  <Typography variant="h3">{appointment.reference_code}</Typography>
                  <StatusChip value={appointment.status} />
                </Stack>
                <Typography><strong>Bác sĩ:</strong> {appointment.doctor_name}</Typography>
                <Typography><strong>Chuyên khoa:</strong> {appointment.specialty_name}</Typography>
                <Typography><strong>Thời gian khám:</strong> {formatDateTime(appointment.slot_start_at)} – {formatDateTime(appointment.slot_end_at)}</Typography>
                <Typography variant="caption" color="text.secondary">Đặt lúc {formatDateTime(appointment.booked_at)}</Typography>
                {appointment.cancellation_reason && <Alert severity="info">Lý do hủy: {appointment.cancellation_reason}</Alert>}
              </Stack>
              {appointment.status === 'CONFIRMED' && <Button color="error" variant="outlined" onClick={() => setCancelId(appointment.id)} sx={{ alignSelf: { xs: 'stretch', sm: 'center' } }}>Hủy lịch</Button>}
            </Stack></CardContent></Card>
          ))}
        </Stack>
      )}
      <Dialog open={Boolean(cancelId)} onClose={() => setCancelId(null)} fullWidth maxWidth="sm">
        <form onSubmit={form.handleSubmit((values) => cancellation.mutate(values))}>
          <DialogTitle>Xác nhận hủy lịch</DialogTitle>
          <DialogContent><Stack spacing={2} sx={{ pt: 1 }}><Alert severity="warning">Lịch hẹn sau khi hủy vẫn được lưu trong lịch sử của bạn.</Alert><TextField autoFocus fullWidth multiline minRows={3} label="Lý do hủy" {...form.register('reason')} error={Boolean(form.formState.errors.reason)} helperText={form.formState.errors.reason?.message} />{cancellation.isError && <ErrorState error={cancellation.error} />}</Stack></DialogContent>
          <DialogActions><Button onClick={() => setCancelId(null)}>Giữ lịch</Button><Button type="submit" color="error" variant="contained" disabled={cancellation.isPending}>Xác nhận hủy</Button></DialogActions>
        </form>
      </Dialog>
    </>
  )
}
