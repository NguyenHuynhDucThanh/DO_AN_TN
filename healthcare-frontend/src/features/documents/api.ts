import { apiClient } from '../../api/client'
import type { DocumentMetadata } from '../../types/domain'

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
export const documentKeys = { all: ['documents'] as const }
export async function listDocuments() {
  const { data } = await apiClient.get<DocumentMetadata[]>('/documents')
  return data
}
export async function createDocument(payload: DocumentPayload) {
  const { data } = await apiClient.post<DocumentMetadata>('/documents', payload)
  return data
}
export async function reviewDocument(id: string, approvalStatus: 'APPROVED' | 'REJECTED') {
  const { data } = await apiClient.post<DocumentMetadata>(`/documents/${id}/review`, { approval_status: approvalStatus })
  return data
}
