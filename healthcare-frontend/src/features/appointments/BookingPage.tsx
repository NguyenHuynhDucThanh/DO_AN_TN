import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Checkbox, FormControl, FormControlLabel, Grid, InputLabel, MenuItem, Select, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { ErrorState, LoadingState, EmptyState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { formatDateTime } from '../../utils/format'
import { doctorKeys, listDoctors } from '../doctors/api'
import { listAvailableSlots, scheduleKeys } from '../schedules/api'
import { listSpecialties, specialtyKeys } from '../specialties/api'
import { appointmentKeys, createAppointment } from './api'

const bookingSchema = z.object({
  slotId: z.string().min(1, 'Hãy chọn một khung giờ.'),
  confirmed: z.boolean().refine(Boolean, 'Bạn cần xác nhận trước khi đặt lịch.'),
})
type BookingValues = z.infer<typeof bookingSchema>

function initialRange() {
  const from = new Date()
  from.setMinutes(from.getMinutes() - from.getTimezoneOffset())
  const to = new Date(from)
  to.setDate(to.getDate() + 30)
  return { from: from.toISOString().slice(0, 16), to: to.toISOString().slice(0, 16) }
}

export function BookingPage() {
  const [params, setParams] = useSearchParams()
  const range = initialRange()
  const specialtyId = params.get('specialty') ?? ''
  const doctorId = params.get('doctor') ?? ''
  const from = params.get('from') ?? range.from
  const to = params.get('to') ?? range.to
  const specialties = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties(true) })
  const doctors = useQuery({ queryKey: [...doctorKeys.all, specialtyId], queryFn: () => listDoctors(specialtyId || undefined, true) })
  const filters = { from_at: new Date(from).toISOString(), to_at: new Date(to).toISOString(), doctor_id: doctorId || undefined, specialty_id: specialtyId || undefined }
  const slots = useQuery({ queryKey: scheduleKeys.available(filters), queryFn: () => listAvailableSlots(filters) })
  const queryClient = useQueryClient()
  const form = useForm<BookingValues>({ resolver: zodResolver(bookingSchema), defaultValues: { slotId: '', confirmed: false } })
  const selectedSlotId = useWatch({ control: form.control, name: 'slotId' })
  const booking = useMutation({
    mutationFn: (values: BookingValues) => createAppointment(values.slotId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['slots', 'available'] }),
        queryClient.invalidateQueries({ queryKey: appointmentKeys.all }),
      ])
      form.reset()
    },
  })

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value); else next.delete(key)
    if (key === 'specialty' && doctorId) next.delete('doctor')
    setParams(next)
    form.setValue('slotId', '')
  }

  return (
    <>
      <PageHeader eyebrow="Đặt lịch thủ công" title="Chọn khung giờ khám" description="Kết quả luôn được kiểm tra lại tại Backend khi xác nhận để tránh double booking." />
      <Card sx={{ mb: 3 }}><CardContent sx={{ p: 3 }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 3 }}><FormControl fullWidth><InputLabel>Chuyên khoa</InputLabel><Select label="Chuyên khoa" value={specialtyId} onChange={(event) => updateParam('specialty', event.target.value)}><MenuItem value="">Tất cả</MenuItem>{specialties.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={{ xs: 12, md: 3 }}><FormControl fullWidth><InputLabel>Bác sĩ</InputLabel><Select label="Bác sĩ" value={doctorId} onChange={(event) => updateParam('doctor', event.target.value)}><MenuItem value="">Tất cả</MenuItem>{doctors.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.user.full_name}</MenuItem>)}</Select></FormControl></Grid>
          <Grid size={{ xs: 12, md: 3 }}><TextField fullWidth type="datetime-local" label="Từ" value={from} onChange={(event) => updateParam('from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /></Grid>
          <Grid size={{ xs: 12, md: 3 }}><TextField fullWidth type="datetime-local" label="Đến" value={to} onChange={(event) => updateParam('to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /></Grid>
        </Grid>
      </CardContent></Card>
      {slots.isPending ? <LoadingState label="Đang tìm khung giờ…" /> : slots.isError ? <ErrorState error={slots.error} onRetry={() => void slots.refetch()} /> : slots.data.length === 0 ? <EmptyState title="Chưa có lịch trống" description="Thay đổi khoảng thời gian, bác sĩ hoặc chuyên khoa để tìm lại." /> : (
        <form onSubmit={form.handleSubmit((values) => booking.mutate(values))}>
          <Grid container spacing={2}>
            {slots.data.map((slot) => (
              <Grid key={slot.id} size={{ xs: 12, sm: 6, lg: 4 }}>
                <Card variant={selectedSlotId === slot.id ? 'outlined' : undefined} sx={{ borderColor: selectedSlotId === slot.id ? 'primary.main' : undefined }}>
                  <CardContent>
                    <Typography variant="h3">{formatDateTime(slot.start_at)}</Typography>
                    <Typography color="text.secondary" sx={{ my: 1 }}>Kết thúc: {formatDateTime(slot.end_at)}</Typography>
                    <Button fullWidth variant={selectedSlotId === slot.id ? 'contained' : 'outlined'} onClick={() => form.setValue('slotId', slot.id, { shouldValidate: true })}>Chọn khung giờ</Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
          <Stack spacing={2} sx={{ mt: 3, maxWidth: 680 }}>
            {form.formState.errors.slotId && <Alert severity="warning">{form.formState.errors.slotId.message}</Alert>}
            <Controller name="confirmed" control={form.control} render={({ field }) => <FormControlLabel control={<Checkbox checked={field.value} onChange={(_, checked) => field.onChange(checked)} />} label="Tôi đã kiểm tra khung giờ và xác nhận đặt lịch." />} />
            {form.formState.errors.confirmed && <Alert severity="warning">{form.formState.errors.confirmed.message}</Alert>}
            {booking.isError && <ErrorState error={booking.error} />}
            {booking.isSuccess && <Alert severity="success">Đặt lịch thành công. Lịch hẹn đã được Backend xác nhận.</Alert>}
            <Button type="submit" variant="contained" size="large" disabled={booking.isPending}>{booking.isPending ? 'Đang xác nhận…' : 'Xác nhận đặt lịch'}</Button>
          </Stack>
        </form>
      )}
    </>
  )
}
