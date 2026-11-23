import { alpha, createTheme } from '@mui/material/styles'

const primary = '#0f766e'
const textPrimary = '#182321'
const border = '#dfe7e5'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: primary, dark: '#0b5f59', light: '#d7efec', contrastText: '#ffffff' },
    secondary: { main: '#526b68', dark: '#344b48', light: '#e7eeec', contrastText: '#ffffff' },
    success: { main: '#2f7d55', light: '#e7f4ec' },
    warning: { main: '#a66a16', light: '#fff4df' },
    error: { main: '#bd3f43', light: '#fdebec' },
    info: { main: '#2c6e9b', light: '#e8f3f9' },
    background: { default: '#f5f8f7', paper: '#ffffff' },
    text: { primary: textPrimary, secondary: '#5e6d6a' },
    divider: border,
  },
  typography: {
    fontFamily: '"Segoe UI Variable", "Segoe UI", Arial, sans-serif',
    h1: { fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 750, lineHeight: 1.12, letterSpacing: '-0.035em' },
    h2: { fontSize: 'clamp(1.7rem, 2.5vw, 2.15rem)', fontWeight: 730, lineHeight: 1.2, letterSpacing: '-0.025em' },
    h3: { fontSize: '1.15rem', fontWeight: 700, lineHeight: 1.35 },
    h4: { fontSize: '1rem', fontWeight: 700, lineHeight: 1.4 },
    h6: { fontSize: '1rem', fontWeight: 700 },
    body1: { fontSize: '0.975rem', lineHeight: 1.65 },
    body2: { fontSize: '0.875rem', lineHeight: 1.55 },
    caption: { fontSize: '0.78rem', lineHeight: 1.45 },
    overline: { fontSize: '0.76rem', fontWeight: 700, lineHeight: 1.5, letterSpacing: '0.035em', textTransform: 'none' },
    button: { textTransform: 'none', fontWeight: 680, letterSpacing: 0 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { minWidth: 320 },
        '::selection': { backgroundColor: alpha(primary, 0.2) },
        '*:focus-visible': { outline: `3px solid ${alpha(primary, 0.28)}`, outlineOffset: 2 },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { minHeight: 40, borderRadius: 10, paddingInline: 16 },
        sizeSmall: { minHeight: 34, paddingInline: 12 },
      },
    },
    MuiCard: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: {
        root: { borderColor: border, boxShadow: '0 1px 2px rgba(20, 44, 40, 0.03)', backgroundImage: 'none' },
      },
    },
    MuiCardContent: {
      styleOverrides: { root: { padding: 24, '&:last-child': { paddingBottom: 24 } } },
    },
    MuiPaper: {
      styleOverrides: { root: { backgroundImage: 'none' }, outlined: { borderColor: border } },
    },
    MuiTextField: { defaultProps: { variant: 'outlined' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 10, backgroundColor: '#ffffff' },
        notchedOutline: { borderColor: '#cbd7d4' },
      },
    },
    MuiInputLabel: { styleOverrides: { root: { color: '#60706d' } } },
    MuiAlert: { styleOverrides: { root: { borderRadius: 10, alignItems: 'center' }, message: { width: '100%' } } },
    MuiChip: { styleOverrides: { root: { borderRadius: 8, fontWeight: 650 }, sizeSmall: { height: 27 } } },
    MuiDialog: {
      styleOverrides: { paper: { borderRadius: 16, border: `1px solid ${border}`, boxShadow: '0 24px 70px rgba(20, 44, 40, 0.16)' } },
    },
    MuiDialogTitle: { styleOverrides: { root: { padding: '24px 24px 12px', fontSize: '1.3rem', fontWeight: 730 } } },
    MuiDialogContent: { styleOverrides: { root: { padding: '12px 24px 20px' } } },
    MuiDialogActions: { styleOverrides: { root: { padding: '12px 24px 24px', gap: 8 } } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 700, backgroundColor: '#f2f6f5' }, root: { borderColor: border } } },
    MuiTooltip: { styleOverrides: { tooltip: { fontSize: '0.78rem' } } },
  },
})
