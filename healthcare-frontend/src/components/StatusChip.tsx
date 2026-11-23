import { Chip, type ChipProps } from '@mui/material'

const labels: Record<string, string> = {
  ACTIVE: 'Đang hoạt động',
  CANCELLED: 'Đã hủy',
  AVAILABLE: 'Còn trống',
  BOOKED: 'Đã đặt',
  BLOCKED: 'Tạm khóa',
  CONFIRMED: 'Đã xác nhận',
  COMPLETED: 'Đã hoàn tất',
  NO_SHOW: 'Không đến',
  PENDING: 'Chờ tiếp nhận',
  IN_PROGRESS: 'Đang xử lý',
  RESOLVED: 'Đã hoàn tất',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Từ chối',
  INACTIVE: 'Ngừng hoạt động',
  NOT_INGESTED: 'Chưa xử lý',
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

export function StatusChip({ value, label }: { value: string; label?: string }) {
  return <Chip size="small" variant="outlined" label={label ?? labels[value] ?? 'Không xác định'} color={colors[value] ?? 'default'} />
}
