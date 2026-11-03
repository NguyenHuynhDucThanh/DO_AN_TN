import { Avatar, Button, Card, CardContent, Divider, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { doctorKeys, getDoctor } from './api'

export function DoctorDetailPage() {
  const { doctorId = '' } = useParams()
  const query = useQuery({ queryKey: doctorKeys.detail(doctorId), queryFn: () => getDoctor(doctorId), enabled: Boolean(doctorId) })
  if (query.isPending) return <LoadingState />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  const doctor = query.data
  return (
    <>
      <PageHeader eyebrow={doctor.specialty.name} title={doctor.user.full_name} description="Thông tin bác sĩ và liên kết tới lịch khám khả dụng." />
      <Card>
        <CardContent sx={{ p: { xs: 3, md: 5 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={4}>
            <Avatar sx={{ width: 112, height: 112, bgcolor: 'primary.light', color: 'primary.dark', fontSize: 42 }}>{doctor.user.full_name.charAt(0)}</Avatar>
            <Stack spacing={2} sx={{ flex: 1 }}>
              <Typography variant="h3">{doctor.specialty.name}</Typography>
              <Typography color="text.secondary">Giấy phép hành nghề: {doctor.license_number}</Typography>
              <Divider />
              <Typography>{doctor.biography || 'Chưa có thông tin giới thiệu.'}</Typography>
              <Typography variant="body2">Email: {doctor.user.email} · Điện thoại: {doctor.user.phone || 'Chưa cập nhật'}</Typography>
              <Button component={RouterLink} to={`/booking?doctor=${doctor.id}`} variant="contained" sx={{ alignSelf: 'flex-start' }}>Xem lịch trống</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </>
  )
}
