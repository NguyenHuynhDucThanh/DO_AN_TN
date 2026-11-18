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
  413: 'Tệp đã chọn vượt quá giới hạn dung lượng cho phép.',
  422: 'Thông tin nhập vào chưa hợp lệ.',
}

export type AppApiError = {
  status?: number
  code?: string
  message: string
}

export function parseApiError(error: unknown): AppApiError {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) {
    return { message: 'Đã xảy ra lỗi. Vui lòng thử lại.' }
  }
  const status = error.response?.status
  const payload = error.response?.data
  const codeMessages: Record<string, string> = {
    email_exists: 'Email này đã được sử dụng.',
    invalid_credentials: 'Email hoặc mật khẩu không đúng.',
    inactive_user: 'Tài khoản hiện không hoạt động.',
    slot_unavailable: 'Khung giờ này không còn khả dụng.',
    slot_occupied: 'Khung giờ này vừa được người khác đặt.',
    slot_in_past: 'Không thể chọn khung giờ đã qua.',
    cancellation_closed: 'Đã quá thời hạn hủy lịch hẹn.',
    invalid_appointment_state: 'Không thể thực hiện thao tác với trạng thái lịch hẹn hiện tại.',
    schedule_overlap: 'Khoảng thời gian này trùng với lịch làm việc đã có.',
    schedule_in_past: 'Không thể tạo lịch làm việc trong quá khứ.',
    schedule_has_slots: 'Không thể sửa lịch làm việc đã có khung giờ khám.',
    slots_exist: 'Các khung giờ khám cho lịch này đã được tạo.',
    specialty_exists: 'Chuyên khoa này đã tồn tại.',
    doctor_exists: 'Hồ sơ bác sĩ này đã tồn tại.',
    doctor_provision_conflict: 'Không thể tạo tài khoản bác sĩ với thông tin đã nhập.',
    document_exists: 'Tài liệu này đã được đăng ký.',
    document_content_exists: 'Tài liệu có nội dung trùng với tài liệu đã tồn tại trong hệ thống.',
    file_too_large: 'Tệp đã chọn vượt quá giới hạn 25 MB.',
    unsupported_document_format: 'Định dạng tài liệu không được hỗ trợ.',
    invalid_document_content: 'Không thể đọc nội dung tệp. Vui lòng kiểm tra lại tài liệu.',
    empty_document: 'Tệp tài liệu không có nội dung.',
    document_not_approved: 'Chỉ tài liệu đã duyệt mới có thể đưa vào kho tri thức.',
    document_ingested: 'Tài liệu đã được xử lý và không thể thực hiện thao tác này.',
    medical_record_exists: 'Lịch hẹn này đã có hồ sơ khám.',
    no_speech_detected: 'Không nhận thấy giọng nói rõ ràng. Vui lòng thử lại.',
    invalid_or_corrupt_audio: 'Không thể đọc bản ghi âm. Vui lòng ghi âm lại.',
    empty_audio: 'Bản ghi âm không có nội dung.',
    audio_too_large: 'Bản ghi âm quá dài. Vui lòng ghi âm một câu ngắn hơn.',
    unsupported_audio_format: 'Thiết bị đã tạo định dạng ghi âm không được hỗ trợ.',
    stt_timeout: 'Việc chuyển giọng nói thành văn bản mất quá nhiều thời gian. Vui lòng thử lại.',
  }
  return {
    status,
    code: payload?.error?.code,
    message:
      (payload?.error?.code ? codeMessages[payload.error.code] : undefined) ||
      (status ? statusMessages[status] : undefined) ||
      (error.code === 'ECONNABORTED'
        ? 'Hệ thống phản hồi quá chậm. Vui lòng thử lại.'
        : 'Không thể kết nối tới hệ thống.'),
  }
}
