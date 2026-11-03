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
      sx={{ mb: 3, justifyContent: 'space-between', alignItems: { xs: 'stretch', sm: 'flex-end' } }}
    >
      <Stack spacing={0.75}>
        {eyebrow && <Typography variant="overline" color="primary.main">{eyebrow}</Typography>}
        <Typography variant="h2">{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ maxWidth: 720 }}>{description}</Typography>}
      </Stack>
      {action}
    </Stack>
  )
}
