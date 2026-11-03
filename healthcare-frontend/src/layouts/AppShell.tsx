import { AppBar, Box, Button, Container, Drawer, IconButton, Stack, Toolbar, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useState } from 'react'
import { Link as RouterLink, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../types/domain'
import { DEV_AUTH_ENABLED } from '../api/client'
import { useAuth } from '../features/auth/AuthContext'
import { DevActorSwitcher } from '../features/dev-auth/DevActorSwitcher'

type NavItem = { label: string; to: string; roles?: Role[] }

const navItems: NavItem[] = [
  { label: 'Trang chủ', to: '/' },
  { label: 'Chuyên khoa', to: '/specialties' },
  { label: 'Bác sĩ', to: '/doctors' },
  { label: 'Chatbot', to: '/chat', roles: ['PATIENT', 'DOCTOR', 'STAFF', 'ADMIN'] },
  { label: 'Tìm lịch trống', to: '/booking' },
  { label: 'Lịch hẹn của tôi', to: '/appointments', roles: ['PATIENT'] },
  { label: 'Lịch sử khám', to: '/medical-history', roles: ['PATIENT'] },
  { label: 'Lịch làm việc', to: '/doctor/schedules', roles: ['DOCTOR'] },
  { label: 'Lịch hẹn phụ trách', to: '/doctor/appointments', roles: ['DOCTOR'] },
  { label: 'Quản lý chuyên khoa', to: '/admin/specialties', roles: ['ADMIN'] },
  { label: 'Quản lý bác sĩ', to: '/admin/doctors', roles: ['ADMIN'] },
  { label: 'Tài liệu RAG', to: '/admin/documents', roles: ['ADMIN', 'STAFF'] },
  { label: 'Yêu cầu hỗ trợ', to: '/handoffs' },
]

export function AppShell() {
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('md'))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { user, status, logout } = useAuth()
  const location = useLocation()
  const visibleItems = navItems.filter((item) => !item.roles || item.roles.some((role) => user?.roles.includes(role)))

  const navigation = (
    <Stack component="nav" spacing={0.5} sx={{ p: 2, minWidth: 250 }}>
      <Typography variant="overline" color="text.secondary" sx={{ px: 1, mb: 1 }}>Điều hướng</Typography>
      {visibleItems.map((item) => (
        <Button
          key={item.to}
          component={RouterLink}
          to={item.to}
          onClick={() => setDrawerOpen(false)}
          variant={location.pathname === item.to ? 'contained' : 'text'}
          color={location.pathname === item.to ? 'primary' : 'inherit'}
          sx={{ justifyContent: 'flex-start' }}
        >
          {item.label}
        </Button>
      ))}
    </Stack>
  )

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <AppBar position="sticky" elevation={0} sx={{ background: 'linear-gradient(110deg, #0e4d4a, #176b66)' }}>
        <Toolbar>
          {!desktop && <IconButton color="inherit" aria-label="Mở menu" onClick={() => setDrawerOpen(true)} sx={{ mr: 1 }}>☰</IconButton>}
          <Typography component={RouterLink} to="/" color="inherit" variant="h6" sx={{ flexGrow: 1, textDecoration: 'none', fontWeight: 750 }}>
            Y tế số
          </Typography>
          {DEV_AUTH_ENABLED && <DevActorSwitcher />}
          {status === 'authenticated' && user ? (
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }}>{user.full_name}</Typography>
              <Button color="inherit" variant="outlined" onClick={() => void logout()} sx={{ borderColor: 'rgba(255,255,255,.5)' }}>Đăng xuất</Button>
            </Stack>
          ) : status === 'anonymous' ? (
            <Button component={RouterLink} to="/login" color="inherit" variant="outlined" sx={{ borderColor: 'rgba(255,255,255,.5)' }}>Đăng nhập</Button>
          ) : null}
        </Toolbar>
      </AppBar>
      <Stack direction="row" sx={{ alignItems: 'stretch' }}>
        {desktop ? <Box component="aside" sx={{ width: 280, flexShrink: 0, borderRight: '1px solid', borderColor: 'divider', minHeight: 'calc(100vh - 64px)', bgcolor: 'background.paper' }}>{navigation}</Box> : (
          <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>{navigation}</Drawer>
        )}
        <Container component="main" maxWidth="xl" sx={{ py: { xs: 3, md: 5 }, minWidth: 0 }}>
          <Outlet />
        </Container>
      </Stack>
    </Box>
  )
}
