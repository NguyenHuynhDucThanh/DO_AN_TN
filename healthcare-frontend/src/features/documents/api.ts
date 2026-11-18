import { apiClient } from '../../api/client'
import type { DocumentContribution, DocumentMetadata } from '../../types/domain'

export type DocumentPayload = {
  title: string
  file_name: string
  file_type: 'CSV' | 'PDF' | 'DOCX'
  storage_key: string
  source_name?: string
  source_url?: string
  checksum_sha256: string
  version_number: number
}
export type ContributionMetadata = {
  title: string
  source_name?: string
  source_url?: string
  author_name?: string
  organization?: string
  publication_year?: number
}

export const documentKeys = {
  all: ['documents'] as const,
  contributions: ['documents', 'contributions', 'me'] as const,
}
export async function listDocuments() {
  const { data } = await apiClient.get<DocumentMetadata[]>('/documents')
  return data
}
export async function createDocument(payload: DocumentPayload) {
  const { data } = await apiClient.post<DocumentMetadata>('/documents', payload)
  return data
}
export async function reviewDocument(id: string, approvalStatus: 'APPROVED' | 'REJECTED', rejectionReason?: string) {
  const { data } = await apiClient.post<DocumentMetadata>(`/documents/${id}/review`, {
    approval_status: approvalStatus,
    rejection_reason: rejectionReason,
  })
  return data
}

export async function ingestDocument(id: string) {
  const { data } = await apiClient.post(`/documents/${id}/ingest`)
  return data
}

export async function downloadDocumentFile(id: string, filename: string) {
  const { data } = await apiClient.get<Blob>(`/documents/${id}/file`, { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function listOwnContributions() {
  const { data } = await apiClient.get<DocumentContribution[]>('/documents/contributions/me')
  return data
}

export async function uploadContribution(file: File, metadata: ContributionMetadata) {
  const form = new FormData()
  form.append('file', file)
  form.append('title', metadata.title)
  for (const [key, value] of Object.entries(metadata)) {
    if (key !== 'title' && value !== undefined && value !== '') form.append(key, String(value))
  }
  const { data } = await apiClient.post<DocumentContribution>('/documents/contributions', form)
  return data
}

export async function updateContribution(id: string, metadata: ContributionMetadata) {
  const { data } = await apiClient.patch<DocumentContribution>(`/documents/contributions/${id}`, metadata)
  return data
}
