import { ThemeProvider } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AUTH_SESSION_EXPIRED_EVENT } from '../api/client'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { RoleRoute } from '../components/RoleRoute'
import { AuthProvider } from '../features/auth/AuthContext'
import { LoginPage } from '../features/auth/LoginPage'
import { RegisterPage } from '../features/auth/RegisterPage'
import { login, logout, register } from '../features/auth/api'
import type { AuthUser } from '../features/auth/types'
import { AppShell } from '../layouts/AppShell'
import { theme } from '../theme/theme'

vi.mock('../features/auth/api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getCurrentUser: vi.fn(),
}))

const patient: AuthUser = {
  id: '77777777-7777-4777-8777-777777777777',
  email: 'patient@example.com',
  full_name: 'Patient Synthetic',
  phone: '0900000098',
  date_of_birth: null,
  gender: null,
  status: 'ACTIVE',
  roles: ['PATIENT'],
  created_at: '2026-10-21T00:00:00Z',
  updated_at: '2026-10-21T00:00:00Z',
}

function axiosError(status: number, detail: string) {
  return Object.assign(new Error(detail), {
    isAxiosError: true,
    response: { status, data: { error: { code: 'test_error', detail } } },
  })
}

function renderAuth(
  ui: React.ReactNode,
  options: { user?: AuthUser | null; path?: string } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider initialUser={options.user ?? null} restoreSession={false}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={[options.path ?? '/']}>{ui}</MemoryRouter>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
})

describe('Phase 5 authentication frontend', () => {
  it('completes the login flow without storing a token', async () => {
    vi.mocked(login).mockResolvedValue(patient)
    const user = userEvent.setup()
    renderAuth(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/appointments" element={<div>Lịch hẹn bảo vệ</div>} />
      </Routes>,
      { path: '/login' },
    )
    await user.type(screen.getByLabelText('Email'), patient.email)
    await user.type(screen.getByLabelText('Mật khẩu'), 'DemoPass123')
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }))
    await waitFor(() => expect(login).toHaveBeenCalledWith({ email: patient.email, password: 'DemoPass123' }))
    expect(window.localStorage.getItem('access_token')).toBeNull()
    expect(window.localStorage.getItem('refresh_token')).toBeNull()
  })

  it('submits Patient registration with required phone', async () => {
    vi.mocked(register).mockResolvedValue(patient)
    const user = userEvent.setup()
    renderAuth(<Routes><Route path="/register" element={<RegisterPage />} /><Route path="/" element={<div>Trang chủ</div>} /></Routes>, { path: '/register' })
    await user.type(screen.getByLabelText('Họ và tên'), patient.full_name)
    await user.type(screen.getByLabelText('Số điện thoại'), patient.phone ?? '')
    await user.type(screen.getByLabelText('Email'), patient.email)
    await user.type(screen.getByLabelText('Mật khẩu'), 'DemoPass123')
    await user.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    await waitFor(() => expect(register).toHaveBeenCalledWith(expect.objectContaining({ phone: patient.phone })))
    expect(await screen.findByText('Trang chủ')).toBeInTheDocument()
  })

  it('logs out and clears the authenticated UI', async () => {
    vi.mocked(logout).mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderAuth(
      <Routes><Route element={<AppShell />}><Route path="/" element={<div>Nội dung</div>} /></Route><Route path="/login" element={<div>Đăng nhập lại</div>} /></Routes>,
      { user: patient },
    )
    await user.click(screen.getByRole('button', { name: 'Đăng xuất' }))
    await waitFor(() => expect(logout).toHaveBeenCalled())
    expect(screen.getByRole('link', { name: 'Đăng nhập' })).toBeInTheDocument()
  })

  it('redirects an anonymous visitor from a protected route', async () => {
    renderAuth(
      <Routes><Route path="/login" element={<div>Trang đăng nhập</div>} /><Route path="/private" element={<ProtectedRoute><div>Bí mật</div></ProtectedRoute>} /></Routes>,
      { path: '/private' },
    )
    expect(await screen.findByText('Trang đăng nhập')).toBeInTheDocument()
    expect(screen.queryByText('Bí mật')).not.toBeInTheDocument()
  })

  it('blocks a role route while keeping Backend authoritative', () => {
    renderAuth(<RoleRoute roles={['ADMIN']}><div>Quản trị</div></RoleRoute>, { user: patient })
    expect(screen.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeInTheDocument()
    expect(screen.queryByText('Quản trị')).not.toBeInTheDocument()
  })

  it('handles an expired session by returning to anonymous state', async () => {
    renderAuth(
      <Routes><Route path="/login" element={<div>Phiên đã hết hạn</div>} /><Route path="/private" element={<ProtectedRoute><div>Đang đăng nhập</div></ProtectedRoute>} /></Routes>,
      { user: patient, path: '/private' },
    )
    expect(screen.getByText('Đang đăng nhập')).toBeInTheDocument()
    window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT))
    expect(await screen.findByText('Phiên đã hết hạn')).toBeInTheDocument()
  })

  it('shows safe 401 feedback and never renders a stack trace', async () => {
    vi.mocked(login).mockRejectedValue(axiosError(401, 'Email hoặc mật khẩu không đúng.'))
    const user = userEvent.setup()
    renderAuth(<LoginPage />, { path: '/login' })
    await user.type(screen.getByLabelText('Email'), patient.email)
    await user.type(screen.getByLabelText('Mật khẩu'), 'WrongPass123')
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }))
    expect(await screen.findByText('Email hoặc mật khẩu không đúng.')).toBeInTheDocument()
    expect(screen.queryByText(/at .*\.tsx/)).not.toBeInTheDocument()
  })
})
