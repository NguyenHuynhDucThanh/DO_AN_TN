import type { PropsWithChildren } from 'react'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './queryClient'
import { theme } from '../theme/theme'
import { DevActorProvider } from '../features/dev-auth/DevActorContext'
import { AuthProvider } from '../features/auth/AuthContext'

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <DevActorProvider>
        <AuthProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </AuthProvider>
      </DevActorProvider>
    </QueryClientProvider>
  )
}
