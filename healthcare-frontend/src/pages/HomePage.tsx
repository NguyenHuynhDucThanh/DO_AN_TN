import { Box, Button, Card, CardContent, Chip, Grid, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

const capabilities = [
  { title: 'Tìm đúng chuyên khoa', text: 'Khám phá chuyên khoa và hồ sơ bác sĩ từ dữ liệu nghiệp vụ của hệ thống.', to: '/specialties' },
  { title: 'Chọn lịch thuận tiện', text: 'Tra cứu slot còn trống theo bác sĩ hoặc chuyên khoa trước khi đặt lịch.', to: '/booking' },
  { title: 'Theo dõi hành trình khám', text: 'Quản lý lịch hẹn và xem hồ sơ kết quả khám của chính bạn.', to: '/appointments' },
]

export function HomePage() {
  return (
    <Stack spacing={{ xs: 5, md: 8 }}>
      <Box sx={{ borderRadius: 4, p: { xs: 3, md: 7 }, color: 'white', background: 'radial-gradient(circle at 85% 15%, rgba(255,255,255,.18), transparent 30%), linear-gradient(130deg, #0e4d4a 0%, #176b66 55%, #2f8880 100%)' }}>
        <Stack spacing={2.5} sx={{ maxWidth: 820 }}>
          <Chip label="AI MVP + Risk Alert · Phase 10" sx={{ alignSelf: 'flex-start', bgcolor: 'rgba(255,255,255,.16)', color: 'white' }} />
          <Typography variant="h1">Chăm sóc sức khỏe bắt đầu từ thông tin rõ ràng.</Typography>
          <Typography variant="h6" sx={{ fontWeight: 400, color: 'rgba(255,255,255,.82)', maxWidth: 700 }}>
            Tra cứu chuyên khoa, chọn bác sĩ, xem lịch trống và đặt hẹn trên một giao diện thống nhất. Phase 7 bổ sung chatbot văn bản cơ bản mà không làm Business MVP phụ thuộc AI.
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <Button component={RouterLink} to="/booking" variant="contained" color="secondary" size="large">Tìm lịch khám</Button>
            <Button component={RouterLink} to="/doctors" variant="outlined" color="inherit" size="large">Xem bác sĩ</Button>
            <Button component={RouterLink} to="/chat" variant="outlined" color="inherit" size="large">Mở chatbot</Button>
          </Stack>
        </Stack>
      </Box>
      <Box>
        <Typography variant="overline" color="primary">Luồng nghiệp vụ cốt lõi</Typography>
        <Typography variant="h2" sx={{ mb: 3 }}>Các việc bạn có thể thực hiện ngay</Typography>
        <Grid container spacing={2.5}>
          {capabilities.map((item, index) => (
            <Grid key={item.title} size={{ xs: 12, md: 4 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography color="secondary.main" sx={{ mb: 3, fontWeight: 800 }}>0{index + 1}</Typography>
                  <Typography variant="h3" gutterBottom>{item.title}</Typography>
                  <Typography color="text.secondary" sx={{ minHeight: 72 }}>{item.text}</Typography>
                  <Button component={RouterLink} to={item.to} sx={{ mt: 2, px: 0 }}>Mở chức năng →</Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  )
}
