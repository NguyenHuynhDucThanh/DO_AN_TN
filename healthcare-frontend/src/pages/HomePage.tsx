import { Box, Button, Card, CardContent, Grid, Paper, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'

const patientCapabilities = [
  { title: 'Tìm chuyên khoa phù hợp', text: 'Xem thông tin chuyên khoa và đội ngũ bác sĩ đang hoạt động.', to: '/specialties' },
  { title: 'Chọn lịch thuận tiện', text: 'Tra cứu khung giờ còn trống theo bác sĩ hoặc chuyên khoa trước khi đặt lịch.', to: '/booking' },
  { title: 'Theo dõi hành trình khám', text: 'Quản lý lịch hẹn và xem hồ sơ kết quả khám của chính bạn.', to: '/appointments' },
]

export function HomePage() {
  const { user } = useAuth()
  const isDoctor = user?.roles.includes('DOCTOR') ?? false
  const isAdmin = user?.roles.includes('ADMIN') ?? false
  const isStaff = user?.roles.includes('STAFF') ?? false
  const capabilities = isAdmin ? [
    { title: 'Quản lý chuyên khoa', text: 'Theo dõi và cập nhật danh mục chuyên khoa của hệ thống.', to: '/admin/specialties' },
    { title: 'Quản lý bác sĩ', text: 'Quản lý tài khoản và hồ sơ chuyên môn của đội ngũ bác sĩ.', to: '/admin/doctors' },
    { title: 'Quản trị tài liệu', text: 'Kiểm duyệt và theo dõi tài liệu trong kho tri thức.', to: '/admin/documents' },
  ] : isDoctor ? [
    { title: 'Quản lý lịch làm việc', text: 'Tạo và theo dõi các khung giờ khám của bạn.', to: '/doctor/schedules' },
    { title: 'Theo dõi lịch hẹn', text: 'Xem và cập nhật các lịch hẹn được phân công.', to: '/doctor/appointments' },
    { title: 'Đóng góp tài liệu', text: 'Gửi tài liệu y khoa để quản trị viên kiểm duyệt.', to: '/doctor/contributions' },
  ] : isStaff ? [
    { title: 'Tiếp nhận hỗ trợ', text: 'Theo dõi các yêu cầu cần được chuyển sang con người hỗ trợ.', to: '/handoffs' },
    { title: 'Quản trị tài liệu', text: 'Theo dõi tài liệu đang chờ xử lý trong hệ thống.', to: '/admin/documents' },
    { title: 'Hỗ trợ qua chatbot', text: 'Tra cứu thông tin sức khỏe và lịch khám trên hệ thống.', to: '/chat' },
  ] : patientCapabilities

  const primaryAction = isAdmin
    ? { label: 'Quản lý bác sĩ', to: '/admin/doctors' }
    : isDoctor
      ? { label: 'Xem lịch làm việc', to: '/doctor/schedules' }
      : isStaff
        ? { label: 'Xem yêu cầu hỗ trợ', to: '/handoffs' }
        : { label: 'Tìm lịch khám', to: '/booking' }

  return (
    <Stack spacing={{ xs: 5, md: 6 }}>
      <Paper variant="outlined" sx={{ overflow: 'hidden', bgcolor: '#eef7f5' }}>
        <Grid container>
          <Grid size={{ xs: 12, lg: 8 }} sx={{ p: { xs: 3, sm: 5, md: 6 } }}>
            <Stack spacing={2.5} sx={{ maxWidth: 760 }}>
              <Typography variant="overline" color="primary.dark">Hỗ trợ tra cứu và đặt lịch</Typography>
              <Typography variant="h1">Chăm sóc sức khỏe bắt đầu từ thông tin rõ ràng</Typography>
              <Typography sx={{ fontSize: { xs: '1rem', md: '1.08rem' }, color: 'text.secondary', maxWidth: 700 }}>
            Tra cứu chuyên khoa, chọn bác sĩ, xem lịch trống và đặt hẹn trên một giao diện thống nhất. Chatbot hỗ trợ giải đáp thông tin sức khỏe phổ thông và tìm lịch khám phù hợp.
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
                <Button component={RouterLink} to={primaryAction.to} variant="contained" size="large">{primaryAction.label}</Button>
                <Button component={RouterLink} to="/doctors" variant="outlined" size="large">Xem bác sĩ</Button>
                <Button component={RouterLink} to="/chat" variant="text" size="large">Mở chatbot</Button>
              </Stack>
            </Stack>
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }} sx={{ display: { xs: 'none', lg: 'grid' }, placeItems: 'center', bgcolor: 'primary.main', color: 'primary.contrastText', p: 5 }}>
            <Stack spacing={1.5} sx={{ textAlign: 'center', maxWidth: 260 }}>
              <Typography sx={{ fontSize: '3.5rem', lineHeight: 1 }} aria-hidden>+</Typography>
              <Typography variant="h3">Chủ động lựa chọn lịch khám</Typography>
              <Typography sx={{ color: 'rgba(255,255,255,.78)' }}>Thông tin bác sĩ, chuyên khoa và khung giờ được cập nhật trong cùng hệ thống.</Typography>
            </Stack>
          </Grid>
        </Grid>
      </Paper>
      <Box>
        <Typography variant="overline" color="primary.dark">Dịch vụ trực tuyến</Typography>
        <Typography variant="h2" sx={{ mb: 3 }}>Các việc bạn có thể thực hiện ngay</Typography>
        <Grid container spacing={2.5}>
          {capabilities.map((item, index) => (
            <Grid key={item.title} size={{ xs: 12, md: 4 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography color="primary.main" variant="overline" sx={{ mb: 2, display: 'block' }}>Bước 0{index + 1}</Typography>
                  <Typography variant="h3" gutterBottom>{item.title}</Typography>
                  <Typography color="text.secondary" sx={{ minHeight: { md: 72 } }}>{item.text}</Typography>
                  <Button component={RouterLink} to={item.to} variant="text" sx={{ mt: 2, px: 0 }}>Mở chức năng</Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  )
}
