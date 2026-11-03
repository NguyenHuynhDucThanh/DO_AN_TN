/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_DEV_PATIENT_ID?: string
  readonly VITE_DEV_DOCTOR_ID?: string
  readonly VITE_DEV_STAFF_ID?: string
  readonly VITE_DEV_ADMIN_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
