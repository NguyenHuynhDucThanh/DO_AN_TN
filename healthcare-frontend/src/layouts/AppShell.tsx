import {
  AppBar, Box, Button, Chip, Container, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemText, Stack, Toolbar, Tooltip, Typography, useMediaQuery, useTheme,
} from '@mui/material'
import { useState } from 'react'
import { Link as RouterLink, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../types/domain'
import { DEV_AUTH_ENABLED } from '../api/client'
import { useAuth } from '../features/auth/AuthContext'
import { DevActorSwitcher } from '../features/dev-auth/DevActorSwitcher'

type NavItem = { label: string; shortLabel: string; to: string; roles?: Role[] }
type NavGroup = { label: string; items: NavItem[] }

const navGroups: NavGroup[] = [
  {
    label: 'Khám phá',
    items: [
      { label: 'Trang chủ', shortLabel: 'TC', to: '/' },
      { label: 'Chuyên khoa', shortLabel: 'CK', to: '/specialties' },
      { label: 'Bác sĩ', shortLabel: 'BS', to: '/doctors' },
    ],
  },
  {
    label: 'Dịch vụ của tôi',
    items: [
      { label: 'Chatbot', shortLabel: 'AI', to: '/chat', roles: ['PATIENT', 'DOCTOR', 'STAFF', 'ADMIN'] },
      { label: 'Tìm lịch trống', shortLabel: 'LT', to: '/booking', roles: ['PATIENT'] },
      { label: 'Lịch hẹn của tôi', shortLabel: 'LH', to: '/appointments', roles: ['PATIENT'] },
      { label: 'Lịch sử khám', shortLabel: 'HS', to: '/medical-history', roles: ['PATIENT'] },
      { label: 'Yêu cầu hỗ trợ', shortLabel: 'HT', to: '/handoffs', roles: ['PATIENT', 'DOCTOR', 'STAFF', 'ADMIN'] },
    ],
  },
  {
    label: 'Công việc bác sĩ',
    items: [
      { label: 'Lịch làm việc', shortLabel: 'LV', to: '/doctor/schedules', roles: ['DOCTOR'] },
      { label: 'Lịch hẹn phụ trách', shortLabel: 'PT', to: '/doctor/appointments', roles: ['DOCTOR'] },
      { label: 'Tài liệu đóng góp', shortLabel: 'TL', to: '/doctor/contributions', roles: ['DOCTOR'] },
    ],
  },
  {
    label: 'Quản lý',
    items: [
      { label: 'Quản lý chuyên khoa', shortLabel: 'CK', to: '/admin/specialties', roles: ['ADMIN'] },
      { label: 'Quản lý bác sĩ', shortLabel: 'BS', to: '/admin/doctors', roles: ['ADMIN'] },
      { label: 'Tài liệu tri thức', shortLabel: 'TT', to: '/admin/documents', roles: ['ADMIN', 'STAFF'] },
    ],
  },
]

const roleLabels: Record<Role, string> = {
  PATIENT: 'Người bệnh', DOCTOR: 'Bác sĩ', STAFF: 'Nhân viên hỗ trợ', ADMIN: 'Quản trị viên',
}

export function AppShell() {
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('md'))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((group) => [group.label, true])),
  )
  const { user, status, logout } = useAuth()
  const location = useLocation()
  const visibleGroups = navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.roles || item.roles.some((role) => user?.roles.includes(role))),
    }))
    .filter((group) => group.items.length > 0)
  const primaryRole = user?.roles[0]
  const toggleGroup = (label: string) => {
    setOpenGroups((current) => ({ ...current, [label]: !current[label] }))
  }

  const navigation = (
    <Stack sx={{ height: '100%', minWidth: desktop ? 0 : 272 }}>
      <Stack direction="row" sx={{ px: sidebarCollapsed && desktop ? 1 : 1.25, py: 1.25, alignItems: 'center', justifyContent: sidebarCollapsed ? 'center' : 'flex-start' }}>
        <Tooltip title={desktop ? (sidebarCollapsed ? 'Mở thanh điều hướng' : 'Thu gọn thanh điều hướng') : 'Đóng menu'}>
          <IconButton
            aria-label={desktop ? (sidebarCollapsed ? 'Mở thanh điều hướng' : 'Thu gọn thanh điều hướng') : 'Đóng thanh điều hướng'}
            onClick={() => desktop ? setSidebarCollapsed((current) => !current) : setDrawerOpen(false)}
            size="small"
          >
            <Box component="span" aria-hidden sx={{ fontSize: '1.25rem', lineHeight: 1 }}>☰</Box>
          </IconButton>
        </Tooltip>
      </Stack>
      <Divider />
      <Box component="nav" aria-label="Điều hướng chính" sx={{ py: 1.5, overflowY: 'auto', flex: 1 }}>
        {visibleGroups.map((group, groupIndex) => (
          <Box key={group.label} sx={{ mb: 1.5 }}>
            {(!desktop || !sidebarCollapsed) && (
              <ListItemButton
                onClick={() => toggleGroup(group.label)}
                aria-expanded={openGroups[group.label]}
                aria-controls={`nav-group-${groupIndex}`}
                sx={{ mx: 1.25, mt: groupIndex ? 1 : 0, mb: 0.5, px: 1.25, minHeight: 38, borderRadius: 1.5 }}
              >
                <ListItemText
                  primary={group.label}
                  slotProps={{ primary: { sx: { color: 'text.secondary', fontSize: '0.78rem', fontWeight: 750 } } }}
                />
                <Box component="span" aria-hidden sx={{ color: 'text.secondary', fontSize: '0.85rem' }}>
                  {openGroups[group.label] ? '▾' : '▸'}
                </Box>
              </ListItemButton>
            )}
            {(desktop && sidebarCollapsed || openGroups[group.label]) && <List id={`nav-group-${groupIndex}`} disablePadding sx={{ px: sidebarCollapsed && desktop ? 1 : 1.25 }}>
              {group.items.map((item) => {
                const active = item.to === '/' ? location.pathname === '/' : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)
                const button = (
                  <ListItemButton
                    key={item.to}
                    component={RouterLink}
                    to={item.to}
                    selected={active}
                    onClick={() => setDrawerOpen(false)}
                    aria-current={active ? 'page' : undefined}
                    sx={{
                      minHeight: 44,
                      px: sidebarCollapsed && desktop ? 0.5 : 1.5,
                      justifyContent: sidebarCollapsed && desktop ? 'center' : 'flex-start',
                      borderRadius: 1.5,
                      mb: 0.25,
                      color: active ? 'primary.dark' : 'text.primary',
                      '&.Mui-selected': { bgcolor: 'primary.light', '&:hover': { bgcolor: 'primary.light' } },
                    }}
                  >
                    {desktop && sidebarCollapsed ? (
                      <Box aria-hidden sx={{ fontSize: '0.72rem', fontWeight: 800, letterSpacing: '0.02em' }}>{item.shortLabel}</Box>
                    ) : (
                      <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontSize: '0.9rem', fontWeight: active ? 700 : 560 } } }} />
                    )}
                  </ListItemButton>
                )
                return desktop && sidebarCollapsed ? <Tooltip key={item.to} title={item.label} placement="right">{button}</Tooltip> : button
              })}
            </List>}
          </Box>
        ))}
      </Box>
    </Stack>
  )

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <AppBar position="sticky" elevation={0} color="inherit" sx={{ borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'rgba(255,255,255,.96)' }}>
        <Toolbar sx={{ minHeight: { xs: 60, sm: 66 } }}>
          {!desktop && <IconButton aria-label="Mở menu" onClick={() => setDrawerOpen(true)} sx={{ mr: 1 }}>☰</IconButton>}
          <Stack component={RouterLink} to="/" direction="row" spacing={1.25} color="inherit" sx={{ flexGrow: 1, alignItems: 'center', textDecoration: 'none' }}>
            <Box aria-hidden sx={{ width: 34, height: 34, borderRadius: 1.5, display: 'grid', placeItems: 'center', bgcolor: 'primary.main', color: 'white', fontWeight: 800 }}>Y</Box>
            <Stack spacing={0}>
              <Typography variant="h6" sx={{ lineHeight: 1.15 }}>Y tế số</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>Tra cứu và đặt lịch khám</Typography>
            </Stack>
          </Stack>
          {DEV_AUTH_ENABLED && <DevActorSwitcher />}
          {status === 'authenticated' && user ? (
            <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
              <Stack spacing={0} sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'flex-end' }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>{user.full_name}</Typography>
                {primaryRole && <Typography variant="caption" color="text.secondary">{roleLabels[primaryRole]}</Typography>}
              </Stack>
              <Button color="inherit" variant="outlined" onClick={() => void logout()}>Đăng xuất</Button>
            </Stack>
          ) : status === 'anonymous' ? (
            <Button component={RouterLink} to="/login" variant="contained">Đăng nhập</Button>
          ) : <Chip size="small" label="Đang xác thực…" />}
        </Toolbar>
      </AppBar>
      <Stack direction="row" sx={{ alignItems: 'stretch' }}>
        {desktop ? (
          <Box component="aside" sx={{ width: sidebarCollapsed ? 72 : 268, flexShrink: 0, borderRight: '1px solid', borderColor: 'divider', minHeight: 'calc(100vh - 66px)', bgcolor: 'background.paper', overflow: 'hidden' }}>
            {navigation}
          </Box>
        ) : (
          <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} slotProps={{ paper: { sx: { width: 288 } } }}>{navigation}</Drawer>
        )}
        <Container component="main" maxWidth="xl" sx={{ py: { xs: 3, md: 4.5 }, px: { xs: 2, sm: 3, lg: 4 }, minWidth: 0 }}>
          <Outlet />
        </Container>
      </Stack>
    </Box>
  )
}
