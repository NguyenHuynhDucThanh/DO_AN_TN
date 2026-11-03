import { Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { RoleRoute } from '../components/RoleRoute'
import { LoadingState } from '../components/AsyncState'
import { AppShell } from '../layouts/AppShell'
import { HomePage } from '../pages/HomePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import {
  BookingPage,
  ChatPage,
  DoctorAdminPage,
  DoctorAppointmentsPage,
  DoctorDetailPage,
  DoctorListPage,
  DoctorMedicalRecordPage,
  DoctorSchedulesPage,
  DocumentAdminPage,
  HandoffPage,
  LoginPage,
  MedicalRecordDetailPage,
  PatientAppointmentsPage,
  PatientMedicalHistoryPage,
  RegisterPage,
  SpecialtyAdminPage,
  SpecialtyDetailPage,
  SpecialtyListPage,
} from './lazyPages'

function deferred(element: ReactNode) {
  return <Suspense fallback={<LoadingState label="Đang tải màn hình…" />}>{element}</Suspense>
}

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/login', element: deferred(<LoginPage />) },
      { path: '/register', element: deferred(<RegisterPage />) },
      { path: '/specialties', element: deferred(<SpecialtyListPage />) },
      { path: '/specialties/:specialtyId', element: deferred(<SpecialtyDetailPage />) },
      { path: '/doctors', element: deferred(<DoctorListPage />) },
      { path: '/doctors/:doctorId', element: deferred(<DoctorDetailPage />) },
      { path: '/booking', element: deferred(<RoleRoute roles={['PATIENT']}><BookingPage /></RoleRoute>) },
      { path: '/appointments', element: deferred(<RoleRoute roles={['PATIENT']}><PatientAppointmentsPage /></RoleRoute>) },
      { path: '/medical-history', element: deferred(<RoleRoute roles={['PATIENT']}><PatientMedicalHistoryPage /></RoleRoute>) },
      { path: '/medical-history/:recordId', element: deferred(<RoleRoute roles={['PATIENT']}><MedicalRecordDetailPage /></RoleRoute>) },
      { path: '/doctor/schedules', element: deferred(<RoleRoute roles={['DOCTOR']}><DoctorSchedulesPage /></RoleRoute>) },
      { path: '/doctor/appointments', element: deferred(<RoleRoute roles={['DOCTOR']}><DoctorAppointmentsPage /></RoleRoute>) },
      { path: '/doctor/appointments/:appointmentId/medical-record', element: deferred(<RoleRoute roles={['DOCTOR']}><DoctorMedicalRecordPage /></RoleRoute>) },
      { path: '/admin/specialties', element: deferred(<RoleRoute roles={['ADMIN']}><SpecialtyAdminPage /></RoleRoute>) },
      { path: '/admin/doctors', element: deferred(<RoleRoute roles={['ADMIN']}><DoctorAdminPage /></RoleRoute>) },
      { path: '/admin/documents', element: deferred(<RoleRoute roles={['ADMIN', 'STAFF']}><DocumentAdminPage /></RoleRoute>) },
      { path: '/handoffs', element: deferred(<ProtectedRoute><HandoffPage /></ProtectedRoute>) },
      { path: '/chat', element: deferred(<ProtectedRoute><ChatPage /></ProtectedRoute>) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
