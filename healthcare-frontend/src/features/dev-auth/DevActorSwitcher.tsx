import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { DEV_ACTOR_CHANGED_EVENT } from '../../api/client'
import type { Role } from '../../types/domain'
import { useDevActor } from './DevActorContext'

const roleLabels: Record<Role, string> = {
  PATIENT: 'Patient', DOCTOR: 'Doctor', STAFF: 'Staff', ADMIN: 'Admin',
}

export function DevActorSwitcher() {
  const { actor, setActor, configuredIds } = useDevActor()
  const [open, setOpen] = useState(false)
  const [draftRole, setDraftRole] = useState<Role>(actor.role)
  const [draftId, setDraftId] = useState(actor.userId)

  const changeRole = (role: Role) => {
    setDraftRole(role)
    setDraftId(configuredIds[role])
  }

  const save = () => {
    setActor({ role: draftRole, userId: draftId.trim() })
    window.dispatchEvent(new Event(DEV_ACTOR_CHANGED_EVENT))
    setOpen(false)
  }

  return (
    <>
      <Button color="inherit" variant="outlined" onClick={() => setOpen(true)} sx={{ borderColor: 'rgba(255,255,255,.5)' }}>
        DEV · {roleLabels[actor.role]}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Danh tính nội bộ development/test</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="warning">
              Chỉ dùng trong development/test. Backend xác minh UUID và role thật trong PostgreSQL; đây không phải đăng nhập production.
            </Alert>
            <TextField select label="Vai trò giao diện" value={draftRole} onChange={(event) => changeRole(event.target.value as Role)}>
              {(Object.keys(roleLabels) as Role[]).map((role) => <MenuItem key={role} value={role}>{roleLabels[role]}</MenuItem>)}
            </TextField>
            <TextField
              label="UUID người dùng demo"
              value={draftId}
              onChange={(event) => setDraftId(event.target.value)}
              placeholder="Lấy từ users.id trong PostgreSQL"
              helperText="Có thể cấu hình sẵn bằng VITE_DEV_PATIENT_ID, VITE_DEV_DOCTOR_ID, VITE_DEV_STAFF_ID và VITE_DEV_ADMIN_ID."
            />
            {!draftId && <Typography color="error.main" variant="body2">Endpoint được bảo vệ sẽ trả 401 cho tới khi có UUID hợp lệ.</Typography>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Đóng</Button>
          <Button variant="contained" onClick={save}>Dùng danh tính này</Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
