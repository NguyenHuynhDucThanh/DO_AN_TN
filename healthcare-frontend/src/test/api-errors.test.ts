import axios from 'axios'
import { describe, expect, it } from 'vitest'
import { parseApiError } from '../api/errors'

describe('user-facing API errors', () => {
  it('maps known business codes without exposing server detail', () => {
    const error = new axios.AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 409,
        statusText: 'Conflict',
        headers: {},
        config: { headers: {} } as never,
        data: { error: { code: 'slot_occupied', detail: 'SQLSTATE private internal detail' } },
      },
    )

    const parsed = parseApiError(error)
    expect(parsed.message).toBe('Khung giờ này vừa được người khác đặt.')
    expect(parsed.message).not.toContain('SQLSTATE')
  })

  it('uses a safe status message for unknown server details', () => {
    const error = new axios.AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: {},
        config: { headers: {} } as never,
        data: { detail: [{ msg: 'internal validation path', loc: ['body', 'secret'] }] },
      },
    )

    expect(parseApiError(error).message).toBe('Thông tin nhập vào chưa hợp lệ.')
  })

  it('maps duplicate document content to a friendly contribution message', () => {
    const error = new axios.AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 409,
        statusText: 'Conflict',
        headers: {},
        config: { headers: {} } as never,
        data: { error: { code: 'document_content_exists', detail: 'private checksum conflict' } },
      },
    )

    expect(parseApiError(error).message).toBe('Tài liệu có nội dung trùng với tài liệu đã tồn tại trong hệ thống.')
  })

  it('does not expose arbitrary runtime errors', () => {
    expect(parseApiError(new Error('private stack detail')).message).toBe('Đã xảy ra lỗi. Vui lòng thử lại.')
  })
})
