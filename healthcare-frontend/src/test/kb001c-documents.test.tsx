import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from '../layouts/AppShell'
import { DocumentAdminPage } from '../features/documents/DocumentAdminPage'
import { DoctorContributionsPage } from '../features/documents/DoctorContributionsPage'
import {
  downloadDocumentFile, ingestDocument, listDocuments, listOwnContributions,
  reviewDocument, updateContribution, uploadContribution,
} from '../features/documents/api'
import type { DocumentContribution, DocumentMetadata, Role } from '../types/domain'
import { theme } from '../theme/theme'

const auth = vi.hoisted(() => ({ roles: ['DOCTOR'] as Role[] }))
vi.mock('../features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'doctor-user', full_name: 'Bác sĩ An', email: 'doctor@example.invalid', roles: auth.roles },
    status: 'authenticated',
    logout: vi.fn(),
  }),
}))
vi.mock('../features/documents/api', () => ({
  documentKeys: { all: ['documents'], contributions: ['documents', 'contributions', 'me'] },
  listDocuments: vi.fn(), reviewDocument: vi.fn(), ingestDocument: vi.fn(), downloadDocumentFile: vi.fn(),
  listOwnContributions: vi.fn(), uploadContribution: vi.fn(), updateContribution: vi.fn(),
}))

const contribution: DocumentContribution = {
  id: 'doc-1', title: 'Hướng dẫn chăm sóc', file_name: 'huong-dan.json', file_type: 'JSON',
  source_name: 'Nguồn công khai', source_url: null, author_name: 'Nguyễn Văn A', organization: 'Tổ chức Y khoa',
  publication_year: 2026, mime_type: 'application/json', file_size_bytes: 128,
  approval_status: 'REJECTED', ingestion_status: 'NOT_INGESTED', uploaded_by: 'doctor-user', approved_at: '2026-11-18T00:00:00Z',
  rejection_reason: 'Cần bổ sung nguồn xuất bản.', created_at: '2026-11-18T00:00:00Z', updated_at: '2026-11-18T00:00:00Z',
}
const adminDocument: DocumentMetadata = {
  ...contribution,
  storage_key: 'data/rag/raw/uploads/internal.json', checksum_sha256: 'a'.repeat(64), version_number: 1,
  uploader_name: 'Bác sĩ An', uploader_email: 'doctor@example.invalid', approved_by: null, ingestion_error: null,
  approval_status: 'PENDING', rejection_reason: null,
}

function renderPage(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><ThemeProvider theme={theme}><MemoryRouter>{ui}</MemoryRouter></ThemeProvider></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  auth.roles = ['DOCTOR']
  vi.mocked(listOwnContributions).mockResolvedValue([contribution])
  vi.mocked(listDocuments).mockResolvedValue([adminDocument])
  vi.mocked(uploadContribution).mockResolvedValue({ ...contribution, id: 'uploaded', approval_status: 'PENDING', rejection_reason: null })
  vi.mocked(updateContribution).mockResolvedValue({ ...contribution, approval_status: 'PENDING', rejection_reason: null })
  vi.mocked(reviewDocument).mockResolvedValue({ ...adminDocument, approval_status: 'APPROVED' })
  vi.mocked(ingestDocument).mockResolvedValue({ document_id: adminDocument.id, chunks_created: 1 })
  vi.mocked(downloadDocumentFile).mockResolvedValue(undefined)
})

describe('KB-001C Doctor contribution UI', () => {
  it('shows own contribution with friendly states, rejection reason and no Admin actions', async () => {
    renderPage(<DoctorContributionsPage />)
    expect(await screen.findByText('Hướng dẫn chăm sóc')).toBeInTheDocument()
    expect(screen.getByText('Bị từ chối')).toBeInTheDocument()
    expect(screen.getByText('Chưa xử lý')).toBeInTheDocument()
    expect(screen.getByText(/Cần bổ sung nguồn xuất bản/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Duyệt' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /kho tri thức/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/storage_key|checksum_sha256/)).not.toBeInTheDocument()
  })

  it('uploads a supported file and refreshes the list', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorContributionsPage />)
    await user.click(screen.getByRole('button', { name: 'Đóng góp tài liệu' }))
    const file = new File(['{"content":"synthetic"}'], 'synthetic.json', { type: 'application/json' })
    await user.upload(screen.getByLabelText('Chọn tệp'), file)
    await user.type(screen.getByLabelText(/Tiêu đề/), 'Tài liệu synthetic')
    await user.click(screen.getByRole('button', { name: 'Gửi tài liệu' }))
    await waitFor(() => expect(uploadContribution).toHaveBeenCalledWith(file, expect.objectContaining({ title: 'Tài liệu synthetic' })))
    await waitFor(() => expect(vi.mocked(listOwnContributions).mock.calls.length).toBeGreaterThanOrEqual(2))
  })

  it('edits and resubmits rejected metadata', async () => {
    const user = userEvent.setup()
    renderPage(<DoctorContributionsPage />)
    await user.click(await screen.findByRole('button', { name: 'Chỉnh sửa và gửi lại' }))
    const title = screen.getByLabelText(/Tiêu đề/)
    await user.clear(title)
    await user.type(title, 'Tài liệu đã bổ sung')
    await user.click(screen.getByRole('button', { name: 'Gửi lại' }))
    await waitFor(() => expect(updateContribution).toHaveBeenCalledWith(contribution.id, expect.objectContaining({ title: 'Tài liệu đã bổ sung' })))
  })
})

describe('KB-001C Admin document UI', () => {
  beforeEach(() => { auth.roles = ['ADMIN'] })

  it('reviews the original file and approves a pending contribution', async () => {
    const user = userEvent.setup()
    renderPage(<DocumentAdminPage />)
    expect(await screen.findByText('Người gửi: Bác sĩ An (doctor@example.invalid)')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Kiểm tra tệp' }))
    await user.click(screen.getByRole('button', { name: 'Duyệt' }))
    await waitFor(() => expect(downloadDocumentFile).toHaveBeenCalledWith(adminDocument.id, adminDocument.file_name))
    await waitFor(() => expect(reviewDocument).toHaveBeenCalledWith(adminDocument.id, 'APPROVED'))
  })

  it('requires a rejection reason and invalidates after rejection', async () => {
    const user = userEvent.setup()
    renderPage(<DocumentAdminPage />)
    await user.click(await screen.findByRole('button', { name: 'Từ chối' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận từ chối' }))
    expect(screen.getByText('Hãy nhập lý do từ chối.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Lý do từ chối'), 'Nguồn chưa đầy đủ')
    await user.click(screen.getByRole('button', { name: 'Xác nhận từ chối' }))
    await waitFor(() => expect(reviewDocument).toHaveBeenCalledWith(adminDocument.id, 'REJECTED', 'Nguồn chưa đầy đủ'))
    await waitFor(() => expect(listDocuments).toHaveBeenCalledTimes(2))
  })

  it('shows ingest only for an approved eligible document', async () => {
    const user = userEvent.setup()
    vi.mocked(listDocuments).mockResolvedValue([{ ...adminDocument, approval_status: 'APPROVED' }])
    renderPage(<DocumentAdminPage />)
    await user.click(await screen.findByRole('button', { name: 'Đưa vào kho tri thức' }))
    await waitFor(() => expect(ingestDocument).toHaveBeenCalledWith(adminDocument.id))
  })

  it('does not expose Admin actions to Staff', async () => {
    auth.roles = ['STAFF']
    renderPage(<DocumentAdminPage />)
    await screen.findByText(adminDocument.title)
    expect(screen.queryByRole('button', { name: 'Duyệt' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Từ chối' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /kho tri thức/i })).not.toBeInTheDocument()
  })
})

describe('KB-001C navigation boundary', () => {
  it('shows the contribution menu only to Doctor', async () => {
    const user = userEvent.setup()
    const view = renderPage(<Routes><Route element={<AppShell />}><Route index element={<Outlet />} /></Route></Routes>)
    await user.click(screen.getByRole('button', { name: 'Mở menu' }))
    expect(screen.getByRole('link', { name: 'Tài liệu đóng góp' })).toBeInTheDocument()
    auth.roles = ['PATIENT']
    view.unmount()
    renderPage(<Routes><Route element={<AppShell />}><Route index element={<Outlet />} /></Route></Routes>)
    await user.click(screen.getByRole('button', { name: 'Mở menu' }))
    expect(screen.queryByRole('link', { name: 'Tài liệu đóng góp' })).not.toBeInTheDocument()
  })
})
