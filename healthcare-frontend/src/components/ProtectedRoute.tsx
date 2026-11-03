import { Navigate, useLocation } from 'react-router-dom'
import { LoadingState } from './AsyncState'
import { useAuth } from '../features/auth/AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <LoadingState label="Đang khôi phục phiên đăng nhập…" />
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }
  return children
}
