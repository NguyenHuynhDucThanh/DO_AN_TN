import { ThemeProvider } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { DevActorProvider } from '../features/dev-auth/DevActorContext'
import { theme } from '../theme/theme'

export function renderPage(ui: ReactElement, path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <DevActorProvider>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
        </ThemeProvider>
      </DevActorProvider>
    </QueryClientProvider>,
  )
}
