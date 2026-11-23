import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { DEV_ACTOR_CHANGED_EVENT } from '../../api/client'
import type { Role } from '../../types/domain'
import { useDevActor } from './DevActorContext'

const roleLabels: Record<Role, string> = {
  PATIENT: 'Người bệnh', DOCTOR: 'Bác sĩ', STAFF: 'Nhân viên hỗ trợ', ADMIN: 'Quản trị viên',
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
        Tài khoản thử · {roleLabels[actor.role]}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Chọn tài khoản thử nghiệm</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="warning">
              Công cụ này chỉ xuất hiện trong môi trường phát triển để kiểm tra giao diện theo từng vai trò.
            </Alert>
            <TextField select label="Vai trò giao diện" value={draftRole} onChange={(event) => changeRole(event.target.value as Role)}>
              {(Object.keys(roleLabels) as Role[]).map((role) => <MenuItem key={role} value={role}>{roleLabels[role]}</MenuItem>)}
            </TextField>
            <TextField
              label="Mã tài khoản thử nghiệm"
              value={draftId}
              onChange={(event) => setDraftId(event.target.value)}
              placeholder="Nhập mã tài khoản đã được cấu hình"
              helperText="Mỗi vai trò cần liên kết với một tài khoản thử nghiệm hợp lệ."
            />
            {!draftId && <Typography color="error.main" variant="body2">Chưa có tài khoản thử nghiệm cho vai trò này.</Typography>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Hủy</Button>
          <Button variant="contained" onClick={save}>Chọn tài khoản</Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
