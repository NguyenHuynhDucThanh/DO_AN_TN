/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState, type PropsWithChildren } from 'react'
import { DEV_ACTOR_STORAGE_KEY } from '../../api/client'
import type { Role } from '../../types/domain'

export type DevActor = { role: Role; userId: string }

type DevActorContextValue = {
  actor: DevActor
  setActor: (actor: DevActor) => void
  configuredIds: Record<Role, string>
}

const configuredIds: Record<Role, string> = {
  PATIENT: import.meta.env.VITE_DEV_PATIENT_ID?.trim() ?? '',
  DOCTOR: import.meta.env.VITE_DEV_DOCTOR_ID?.trim() ?? '',
  STAFF: import.meta.env.VITE_DEV_STAFF_ID?.trim() ?? '',
  ADMIN: import.meta.env.VITE_DEV_ADMIN_ID?.trim() ?? '',
}

const DevActorContext = createContext<DevActorContextValue | null>(null)

function initialActor(): DevActor {
  const saved = window.localStorage.getItem(DEV_ACTOR_STORAGE_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved) as DevActor
      if (parsed.role && typeof parsed.userId === 'string') return parsed
    } catch {
      window.localStorage.removeItem(DEV_ACTOR_STORAGE_KEY)
    }
  }
  const role: Role = 'PATIENT'
  const actor = { role, userId: configuredIds[role] }
  if (actor.userId) window.localStorage.setItem(DEV_ACTOR_STORAGE_KEY, JSON.stringify(actor))
  return actor
}

export function DevActorProvider({ children }: PropsWithChildren) {
  const [actor, setActorState] = useState<DevActor>(initialActor)
  const value = useMemo<DevActorContextValue>(
    () => ({
      actor,
      configuredIds,
      setActor: (next) => {
        setActorState(next)
        if (next.userId) window.localStorage.setItem(DEV_ACTOR_STORAGE_KEY, JSON.stringify(next))
        else window.localStorage.removeItem(DEV_ACTOR_STORAGE_KEY)
      },
    }),
    [actor],
  )
  return <DevActorContext.Provider value={value}>{children}</DevActorContext.Provider>
}

export function useDevActor() {
  const value = useContext(DevActorContext)
  if (!value) throw new Error('useDevActor must be used inside DevActorProvider')
  return value
}
