import axios from 'axios'

type ApiErrorPayload = {
  error?: { code?: string; detail?: string }
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>
}

const statusMessages: Record<number, string> = {
  400: 'Dữ liệu gửi lên không phù hợp với quy tắc nghiệp vụ.',
  401: 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.',
  403: 'Bạn không có quyền thực hiện thao tác này.',
  404: 'Không tìm thấy dữ liệu được yêu cầu.',
  409: 'Dữ liệu vừa thay đổi hoặc đang xung đột. Vui lòng tải lại và thử lại.',
  422: 'Thông tin nhập vào chưa hợp lệ.',
}

export type AppApiError = {
  status?: number
  code?: string
  message: string
}

export function parseApiError(error: unknown): AppApiError {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) {
    return { message: error instanceof Error ? error.message : 'Đã xảy ra lỗi không xác định.' }
  }
  const status = error.response?.status
  const payload = error.response?.data
  const validationDetail = Array.isArray(payload?.detail)
    ? payload.detail.map((item) => item.msg).filter(Boolean).join(' ')
    : undefined
  return {
    status,
    code: payload?.error?.code,
    message:
      payload?.error?.detail ||
      validationDetail ||
      (typeof payload?.detail === 'string' ? payload.detail : undefined) ||
      (status ? statusMessages[status] : undefined) ||
      (error.code === 'ECONNABORTED'
        ? 'Backend phản hồi quá chậm. Vui lòng thử lại.'
        : 'Không thể kết nối tới Backend.'),
  }
}
