import { Avatar, Card, CardActionArea, CardContent, FormControl, Grid, InputLabel, MenuItem, Select, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useSearchParams } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { listSpecialties, specialtyKeys } from '../specialties/api'
import { doctorKeys, listDoctors } from './api'

export function DoctorListPage() {
  const [params, setParams] = useSearchParams()
  const specialtyId = params.get('specialty') ?? ''
  const specialties = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties(true) })
  const doctors = useQuery({ queryKey: [...doctorKeys.all, specialtyId], queryFn: () => listDoctors(specialtyId || undefined, true) })
  return (
    <>
      <PageHeader
        eyebrow="Tra cứu"
        title="Đội ngũ bác sĩ"
        description="Lọc theo chuyên khoa và xem thông tin phục vụ lựa chọn lịch khám."
        action={
          <FormControl size="small" sx={{ minWidth: 240 }}>
            <InputLabel>Chuyên khoa</InputLabel>
            <Select label="Chuyên khoa" value={specialtyId} onChange={(event) => setParams(event.target.value ? { specialty: event.target.value } : {})}>
              <MenuItem value="">Tất cả chuyên khoa</MenuItem>
              {specialties.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
            </Select>
          </FormControl>
        }
      />
      {doctors.isPending ? <LoadingState /> : doctors.isError ? <ErrorState error={doctors.error} onRetry={() => void doctors.refetch()} /> : doctors.data.length === 0 ? (
        <EmptyState title="Không có bác sĩ phù hợp" description="Thử chọn chuyên khoa khác hoặc quay lại sau." />
      ) : (
        <Grid container spacing={2}>
          {doctors.data.map((doctor) => (
            <Grid key={doctor.id} size={{ xs: 12, md: 6, xl: 4 }}>
              <Card sx={{ height: '100%' }}>
                <CardActionArea component={RouterLink} to={`/doctors/${doctor.id}`} sx={{ height: '100%' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Stack direction="row" spacing={2.5} sx={{ alignItems: 'flex-start' }}>
                      <Avatar sx={{ width: 56, height: 56, bgcolor: 'primary.light', color: 'primary.dark', fontWeight: 800 }}>{doctor.user.full_name.charAt(0)}</Avatar>
                      <Stack spacing={0.5}>
                        <Typography variant="h3">{doctor.user.full_name}</Typography>
                        <Typography color="primary.main" sx={{ fontWeight: 650 }}>{doctor.specialty.name}</Typography>
                        <Typography variant="body2" color="text.secondary">Số giấy phép: {doctor.license_number}</Typography>
                        <Typography sx={{ pt: 1 }}>{doctor.biography || 'Chưa có giới thiệu.'}</Typography>
                      </Stack>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </>
  )
}
