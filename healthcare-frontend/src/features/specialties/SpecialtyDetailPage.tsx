import { Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { getSpecialty, specialtyKeys } from './api'

export function SpecialtyDetailPage() {
  const { specialtyId = '' } = useParams()
  const query = useQuery({ queryKey: specialtyKeys.detail(specialtyId), queryFn: () => getSpecialty(specialtyId), enabled: Boolean(specialtyId) })
  if (query.isPending) return <LoadingState />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  return (
    <>
      <PageHeader eyebrow={query.data.code} title={query.data.name} description="Thông tin chuyên khoa từ Backend Phase 3." />
      <Card>
        <CardContent sx={{ p: { xs: 3, md: 5 } }}>
          <Stack spacing={3}>
            <Typography sx={{ fontSize: '1.1rem' }} color="text.secondary">{query.data.description || 'Chưa có mô tả cho chuyên khoa này.'}</Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <Button component={RouterLink} to={`/doctors?specialty=${query.data.id}`} variant="contained">Xem bác sĩ</Button>
              <Button component={RouterLink} to={`/booking?specialty=${query.data.id}`} variant="outlined">Tìm lịch trống</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </>
  )
}
