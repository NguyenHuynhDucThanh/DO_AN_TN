import { Card, CardActionArea, CardContent, Grid, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../../components/AsyncState'
import { PageHeader } from '../../components/PageHeader'
import { listSpecialties, specialtyKeys } from './api'

export function SpecialtyListPage() {
  const query = useQuery({ queryKey: specialtyKeys.all, queryFn: () => listSpecialties(true) })
  return (
    <>
      <PageHeader eyebrow="Tra cứu" title="Chuyên khoa" description="Chọn nhóm chuyên môn phù hợp để xem bác sĩ đang hoạt động và lịch khám khả dụng." />
      {query.isPending ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.length === 0 ? (
        <EmptyState title="Chưa có chuyên khoa" description="Dữ liệu chuyên khoa đang hoạt động sẽ xuất hiện tại đây." />
      ) : (
        <Grid container spacing={2}>
          {query.data.map((specialty) => (
            <Grid key={specialty.id} size={{ xs: 12, sm: 6, lg: 4 }}>
              <Card sx={{ height: '100%' }}>
                <CardActionArea component={RouterLink} to={`/specialties/${specialty.id}`} sx={{ height: '100%' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={1.5}>
                      <Typography variant="overline" color="primary">{specialty.code}</Typography>
                      <Typography variant="h3">{specialty.name}</Typography>
                      <Typography color="text.secondary">{specialty.description || 'Chưa có mô tả.'}</Typography>
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
