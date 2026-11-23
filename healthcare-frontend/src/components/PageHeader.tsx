import { Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      spacing={2}
      sx={{ mb: { xs: 3, md: 4 }, justifyContent: 'space-between', alignItems: { xs: 'stretch', sm: 'center' } }}
    >
      <Stack spacing={0.65} sx={{ minWidth: 0 }}>
        {eyebrow && <Typography variant="overline" color="primary.dark">{eyebrow}</Typography>}
        <Typography component="h1" variant="h2">{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ maxWidth: 760 }}>{description}</Typography>}
      </Stack>
      {action && <Stack direction="row" sx={{ flexShrink: 0 }}>{action}</Stack>}
    </Stack>
  )
}
