import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Button, Card, CardContent, Stack, TextField } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useParams } from 'react-router-dom'
import { z } from 'zod'
import { parseApiError } from '../../api/errors'
import { ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { createMedicalRecord, getMedicalRecordByAppointment, medicalRecordKeys, updateMedicalRecord, type MedicalRecordPayload } from './api'

const schema = z.object({
  symptoms: z.string().trim().min(1, 'Hãy nhập triệu chứng ghi nhận.').max(10000),
  clinical_notes: z.string().trim().min(1, 'Hãy nhập ghi chú khám.').max(20000),
  doctor_conclusion: z.string().trim().min(1, 'Hãy nhập kết luận của bác sĩ.').max(10000),
  follow_up_instructions: z.string().trim().min(1, 'Hãy nhập hướng dẫn sau khám.').max(10000),
})
type Values = z.infer<typeof schema>

export function DoctorMedicalRecordPage() {
  const { appointmentId = '' } = useParams()
  const queryClient = useQueryClient()
  const record = useQuery({
    queryKey: medicalRecordKeys.appointment(appointmentId),
    queryFn: () => getMedicalRecordByAppointment(appointmentId),
    enabled: Boolean(appointmentId),
    retry: false,
  })
  const notFound = record.isError && parseApiError(record.error).status === 404
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { symptoms: '', clinical_notes: '', doctor_conclusion: '', follow_up_instructions: '' },
  })

  useEffect(() => {
    if (record.data) {
      form.reset({
        symptoms: record.data.symptoms,
        clinical_notes: record.data.clinical_notes,
        doctor_conclusion: record.data.doctor_conclusion,
        follow_up_instructions: record.data.follow_up_instructions,
      })
    }
  }, [record.data, form])

  const save = useMutation({
    mutationFn: (values: Values) => record.data
      ? updateMedicalRecord(record.data.id, values as Omit<MedicalRecordPayload, 'appointment_id'>)
      : createMedicalRecord({ appointment_id: appointmentId, ...values }),
    onSuccess: async (saved) => {
      queryClient.setQueryData(medicalRecordKeys.appointment(appointmentId), saved)
      await queryClient.invalidateQueries({ queryKey: medicalRecordKeys.history })
    },
  })

  if (record.isPending) return <LoadingState />
  if (record.isError && !notFound) return <ErrorState error={record.error} onRetry={() => void record.refetch()} />
  return (
    <>
      <PageHeader eyebrow="Doctor · Dữ liệu lâm sàng" title={record.data ? 'Cập nhật hồ sơ khám' : 'Lập hồ sơ khám'} description="Backend kiểm tra Appointment đã COMPLETED và thuộc đúng bác sĩ trước khi lưu." />
      <Alert severity="warning" sx={{ mb: 2 }}>Chỉ dùng dữ liệu synthetic/demo. Nội dung này không được đưa vào RAG hoặc Gemini.</Alert>
      <Card><CardContent sx={{ p: { xs: 3, md: 5 } }}>
        <form onSubmit={form.handleSubmit((values) => save.mutate(values))}>
          <Stack spacing={2.5}>
            <TextField multiline minRows={3} label="Triệu chứng ghi nhận" {...form.register('symptoms')} error={Boolean(form.formState.errors.symptoms)} helperText={form.formState.errors.symptoms?.message} />
            <TextField multiline minRows={4} label="Ghi chú khám" {...form.register('clinical_notes')} error={Boolean(form.formState.errors.clinical_notes)} helperText={form.formState.errors.clinical_notes?.message} />
            <TextField multiline minRows={3} label="Kết luận do bác sĩ nhập" {...form.register('doctor_conclusion')} error={Boolean(form.formState.errors.doctor_conclusion)} helperText={form.formState.errors.doctor_conclusion?.message} />
            <TextField multiline minRows={3} label="Hướng dẫn sau khám" {...form.register('follow_up_instructions')} error={Boolean(form.formState.errors.follow_up_instructions)} helperText={form.formState.errors.follow_up_instructions?.message} />
            {save.isError && <ErrorState error={save.error} />}
            {save.isSuccess && <Alert severity="success">Hồ sơ khám đã được lưu thành công.</Alert>}
            <Button type="submit" variant="contained" size="large" disabled={save.isPending}>{save.isPending ? 'Đang lưu…' : record.data ? 'Lưu cập nhật' : 'Tạo hồ sơ khám'}</Button>
          </Stack>
        </form>
      </CardContent></Card>
    </>
  )
}
