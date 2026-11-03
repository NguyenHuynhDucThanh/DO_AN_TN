import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    primary: { main: '#176b66', dark: '#0e4d4a', light: '#d8efec' },
    secondary: { main: '#d78038' },
    background: { default: '#f4f7f6', paper: '#ffffff' },
  },
  typography: {
    fontFamily: '"Segoe UI Variable", "Segoe UI", Arial, sans-serif',
    h1: { fontSize: 'clamp(2rem, 4vw, 3.4rem)', fontWeight: 720, lineHeight: 1.08 },
    h2: { fontSize: 'clamp(1.55rem, 2.5vw, 2.2rem)', fontWeight: 700 },
    h3: { fontSize: '1.25rem', fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 650 },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiCard: { styleOverrides: { root: { boxShadow: '0 10px 32px rgba(31, 61, 57, 0.07)' } } },
    MuiButton: { defaultProps: { disableElevation: true } },
  },
})
