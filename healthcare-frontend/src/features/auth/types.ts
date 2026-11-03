import type { Role } from '../../types/domain'

export type AuthUser = {
  id: string
  email: string
  full_name: string
  phone: string | null
  date_of_birth: string | null
  gender: 'FEMALE' | 'MALE' | 'OTHER' | 'UNDISCLOSED' | null
  status: 'ACTIVE' | 'INACTIVE' | 'LOCKED'
  roles: Role[]
  created_at: string
  updated_at: string
}

export type LoginInput = { email: string; password: string }

export type RegisterInput = LoginInput & {
  full_name: string
  phone: string
  date_of_birth?: string | null
  gender?: AuthUser['gender']
}
