import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { StatusChip } from '../../components/StatusChip'
import type { Schedule } from '../../types/domain'
import { formatDateTime } from '../../utils/format'
import { useAuth } from '../auth/AuthContext'
import { doctorKeys, listDoctors } from '../doctors/api'
import {
  createSchedule, generateSlots, listScheduleSlots, listSchedules, scheduleKeys, setSlotStatus, updateSchedule,
} from './api'

const scheduleSchema = z.object({
  start_at: z.string().min(1, 'Hãy chọn thời gian bắt đầu.'),
  end_at: z.string().min(1, 'Hãy chọn thời gian kết thúc.'),
  slot_duration_minutes: z.number().int().min(5).max(480),
}).superRefine((values, context) => {
  const start = new Date(values.start_at)
  const end = new Date(values.end_at)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
    context.addIssue({ code: 'custom', path: ['end_at'], message: 'Thời gian kết thúc phải sau thời gian bắt đầu.' })
    return
  }
  if ((end.getTime() - start.getTime()) % (values.slot_duration_minutes * 60_000) !== 0) {
    context.addIssue({ code: 'custom', path: ['slot_duration_minutes'], message: 'Khoảng thời gian phải chia hết cho thời lượng mỗi khung giờ.' })
  }
})
type ScheduleValues = z.infer<typeof scheduleSchema>

function toLocalInput(iso: string) {
  const date = new Date(iso)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function ScheduleCard({ schedule, onEdit }: { schedule: Schedule; onEdit: (schedule: Schedule) => void }) {
  const client = useQueryClient()
  const slots = useQuery({ queryKey: scheduleKeys.slots(schedule.id), queryFn: () => listScheduleSlots(schedule.id) })
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: scheduleKeys.all }),
      client.invalidateQueries({ queryKey: scheduleKeys.slots(schedule.id) }),
      client.invalidateQueries({ queryKey: ['slots'] }),
    ])
  }
  const generate = useMutation({ mutationFn: () => generateSlots(schedule.id), onSuccess: refresh })
  const changeSlot = useMutation({ mutationFn: ({ id, blocked }: { id: string; blocked: boolean }) => setSlotStatus(id, blocked), onSuccess: refresh })
  const cancel = useMutation({ mutationFn: () => updateSchedule(schedule.id, { status: 'CANCELLED' }), onSuccess: refresh })
  const error = generate.error ?? changeSlot.error ?? cancel.error
  const isActive = schedule.status === 'ACTIVE'
  return (
    <Card><CardContent><Stack spacing={2}>
      <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ justifyContent: 'space-between', gap: 2 }}>
        <Stack><Typography variant="h3">{formatDateTime(schedule.start_at)}</Typography><Typography color="text.secondary">Kết thúc {formatDateTime(schedule.end_at)} · {schedule.slot_duration_minutes} phút/khung giờ</Typography></Stack>
        <StatusChip value={schedule.status} />
      </Stack>
      {error && <ErrorState error={error} />}
      {slots.isPending ? <LoadingState label="Đang tải khung giờ…" /> : slots.isError ? <ErrorState error={slots.error} onRetry={() => void slots.refetch()} /> : slots.data.length === 0 ? (
        <Alert severity="info">Lịch chưa có khung giờ khám. Hãy tạo khung giờ để người bệnh có thể đặt lịch.</Alert>
      ) : (
        <Stack spacing={1}>{slots.data.map((slot) => <Stack key={slot.id} direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}><Typography>{formatDateTime(slot.start_at)} – {formatDateTime(slot.end_at)}</Typography><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><StatusChip value={slot.status} />{isActive && slot.status !== 'BOOKED' && <Button size="small" onClick={() => changeSlot.mutate({ id: slot.id, blocked: slot.status === 'AVAILABLE' })} disabled={changeSlot.isPending}>{slot.status === 'AVAILABLE' ? 'Chặn' : 'Mở lại'}</Button>}</Stack></Stack>)}</Stack>
      )}
      {isActive && <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>
        {slots.data?.length === 0 && <Button variant="contained" onClick={() => generate.mutate()} disabled={generate.isPending}>{generate.isPending ? 'Đang tạo…' : 'Tạo khung giờ'}</Button>}
        {slots.data?.length === 0 && <Button onClick={() => onEdit(schedule)}>Chỉnh sửa lịch</Button>}
        <Button color="error" onClick={() => { if (window.confirm('Hủy lịch làm việc này?')) cancel.mutate() }} disabled={cancel.isPending}>Hủy lịch</Button>
      </Stack>}
    </Stack></CardContent></Card>
  )
}

function ScheduleDialog({ doctorId, editing, onClose }: { doctorId: string; editing: Schedule | 'new'; onClose: () => void }) {
  const client = useQueryClient()
  const form = useForm<ScheduleValues>({ resolver: zodResolver(scheduleSchema), defaultValues: { start_at: '', end_at: '', slot_duration_minutes: 30 } })
  useEffect(() => {
    if (editing === 'new') form.reset({ start_at: '', end_at: '', slot_duration_minutes: 30 })
    else form.reset({ start_at: toLocalInput(editing.start_at), end_at: toLocalInput(editing.end_at), slot_duration_minutes: editing.slot_duration_minutes })
  }, [editing, form])
  const save = useMutation({
    mutationFn: (values: ScheduleValues) => {
      const payload = { start_at: new Date(values.start_at).toISOString(), end_at: new Date(values.end_at).toISOString(), slot_duration_minutes: values.slot_duration_minutes }
      return editing === 'new' ? createSchedule({ doctor_id: doctorId, ...payload }) : updateSchedule(editing.id, payload)
    },
    onSuccess: async () => { await client.invalidateQueries({ queryKey: scheduleKeys.all }); onClose() },
  })
  return <Dialog open onClose={onClose} fullWidth maxWidth="sm"><form onSubmit={form.handleSubmit((values) => save.mutate(values))}><DialogTitle>{editing === 'new' ? 'Tạo lịch làm việc' : 'Chỉnh sửa lịch làm việc'}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{save.isError && <ErrorState error={save.error} />}<TextField label="Bắt đầu" type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} {...form.register('start_at')} error={Boolean(form.formState.errors.start_at)} helperText={form.formState.errors.start_at?.message} /><TextField label="Kết thúc" type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} {...form.register('end_at')} error={Boolean(form.formState.errors.end_at)} helperText={form.formState.errors.end_at?.message} /><TextField label="Thời lượng mỗi khung giờ (phút)" type="number" {...form.register('slot_duration_minutes', { valueAsNumber: true })} error={Boolean(form.formState.errors.slot_duration_minutes)} helperText={form.formState.errors.slot_duration_minutes?.message} /></Stack></DialogContent><DialogActions><Button onClick={onClose}>Đóng</Button><Button type="submit" variant="contained" disabled={save.isPending}>{save.isPending ? 'Đang lưu…' : 'Lưu'}</Button></DialogActions></form></Dialog>
}

export function DoctorSchedulesPage() {
  const { user } = useAuth()
  const doctors = useQuery({ queryKey: doctorKeys.all, queryFn: () => listDoctors(undefined, true) })
  const doctor = doctors.data?.find((item) => item.user_id === user?.id)
  const schedules = useQuery({ queryKey: scheduleKeys.byDoctor(doctor?.id ?? ''), queryFn: () => listSchedules(doctor?.id), enabled: Boolean(doctor) })
  const [editing, setEditing] = useState<Schedule | 'new' | null>(null)
  return (
    <>
      <PageHeader eyebrow="Dành cho bác sĩ" title="Lịch làm việc" description="Tạo lịch và quản lý các khung giờ để người bệnh có thể đặt khám." action={doctor ? <Button variant="contained" onClick={() => setEditing('new')}>Tạo lịch</Button> : undefined} />
      {!user && <Alert severity="warning">Vui lòng đăng nhập bằng tài khoản bác sĩ.</Alert>}
      {doctors.isPending || (doctor && schedules.isPending) ? <LoadingState /> : doctors.isError ? <ErrorState error={doctors.error} /> : !doctor ? <EmptyState title="Không tìm thấy hồ sơ bác sĩ" description="Tài khoản đang đăng nhập chưa liên kết với hồ sơ bác sĩ đang hoạt động." /> : schedules.isError ? <ErrorState error={schedules.error} onRetry={() => void schedules.refetch()} /> : !schedules.data?.length ? <EmptyState title="Chưa có lịch làm việc" description="Bấm Tạo lịch để thêm lịch làm việc và tạo các khung giờ khám." /> : <Grid container spacing={2}>{schedules.data.map((schedule) => <Grid key={schedule.id} size={{ xs: 12, lg: 6 }}><ScheduleCard schedule={schedule} onEdit={setEditing} /></Grid>)}</Grid>}
      {doctor && editing && <ScheduleDialog doctorId={doctor.id} editing={editing} onClose={() => setEditing(null)} />}
    </>
  )
}
