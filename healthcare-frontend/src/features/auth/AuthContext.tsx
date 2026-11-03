/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AUTH_SESSION_EXPIRED_EVENT, DEV_ACTOR_CHANGED_EVENT } from '../../api/client'
import { getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from './api'
import type { AuthUser, LoginInput, RegisterInput } from './types'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

type AuthContextValue = {
  user: AuthUser | null
  status: AuthStatus
  login: (input: LoginInput) => Promise<AuthUser>
  register: (input: RegisterInput) => Promise<AuthUser>
  logout: () => Promise<void>
  restore: () => Promise<void>
}

type AuthProviderProps = PropsWithChildren<{
  initialUser?: AuthUser | null
  restoreSession?: boolean
}>

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children, initialUser = null, restoreSession = true }: AuthProviderProps) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<AuthUser | null>(initialUser)
  const [status, setStatus] = useState<AuthStatus>(initialUser ? 'authenticated' : restoreSession ? 'loading' : 'anonymous')

  const resetSession = useCallback(() => {
    setUser(null)
    setStatus('anonymous')
    queryClient.clear()
  }, [queryClient])

  const restore = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
      setStatus('authenticated')
    } catch {
      resetSession()
    }
  }, [resetSession])

  useEffect(() => {
    if (!restoreSession) return undefined
    const bootstrap = window.setTimeout(() => void restore(), 0)
    return () => window.clearTimeout(bootstrap)
  }, [restore, restoreSession])

  useEffect(() => {
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, resetSession)
    window.addEventListener(DEV_ACTOR_CHANGED_EVENT, restore)
    return () => {
      window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, resetSession)
      window.removeEventListener(DEV_ACTOR_CHANGED_EVENT, restore)
    }
  }, [resetSession, restore])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    status,
    login: async (input) => {
      const currentUser = await loginRequest(input)
      queryClient.clear()
      setUser(currentUser)
      setStatus('authenticated')
      return currentUser
    },
    register: async (input) => {
      const currentUser = await registerRequest(input)
      queryClient.clear()
      setUser(currentUser)
      setStatus('authenticated')
      return currentUser
    },
    logout: async () => {
      try {
        await logoutRequest()
      } finally {
        resetSession()
      }
    },
    restore,
  }), [queryClient, resetSession, restore, status, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
