import { Chip, type ChipProps } from '@mui/material'

const labels: Record<string, string> = {
  ACTIVE: 'Đang hoạt động',
  CANCELLED: 'Đã hủy',
  AVAILABLE: 'Còn trống',
  BOOKED: 'Đã đặt',
  BLOCKED: 'Đã khóa',
  CONFIRMED: 'Đã xác nhận',
  COMPLETED: 'Đã khám',
  NO_SHOW: 'Không đến',
  PENDING: 'Chờ xử lý',
  IN_PROGRESS: 'Đang xử lý',
  RESOLVED: 'Đã giải quyết',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Từ chối',
  NOT_INGESTED: 'Chưa ingest',
  PROCESSING: 'Đang xử lý',
  FAILED: 'Thất bại',
  NORMAL: 'Bình thường',
  HIGH: 'Cao',
  URGENT: 'Khẩn',
}

const colors: Record<string, ChipProps['color']> = {
  ACTIVE: 'success', AVAILABLE: 'success', COMPLETED: 'success', APPROVED: 'success', RESOLVED: 'success',
  CONFIRMED: 'info', IN_PROGRESS: 'info', PROCESSING: 'info',
  PENDING: 'warning', HIGH: 'warning',
  CANCELLED: 'default', BLOCKED: 'default', NOT_INGESTED: 'default', NORMAL: 'default',
  NO_SHOW: 'error', REJECTED: 'error', FAILED: 'error', URGENT: 'error',
}

export function StatusChip({ value }: { value: string }) {
  return <Chip size="small" label={labels[value] ?? value} color={colors[value] ?? 'default'} />
}
