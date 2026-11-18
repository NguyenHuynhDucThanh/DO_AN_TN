import { expect, type Locator, type Page, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.dirname(fileURLToPath(import.meta.url))
const backendRoot = path.resolve(frontendRoot, '..', '..', 'healthcare-backend')

const adminEmail = 'admin.demo@example.invalid'
const staffEmail = 'staff.demo@example.invalid'
const adminPassword = process.env.E2E_ADMIN_PASSWORD
const staffPassword = process.env.E2E_STAFF_PASSWORD

async function login(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu').fill(password)
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
}

async function logout(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất' }).click()
  await expect(page.getByRole('button', { name: 'Đăng nhập' })).toBeVisible()
}

async function selectMuiOption(page: Page, scope: Page | Locator, label: string, option: string) {
  await scope.getByRole('combobox', { name: label, exact: true }).click()
  await page.getByRole('option', { name: option }).click()
}

function localDateTimeValue(value: Date) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function prepareDoctorCandidate(email: string, fullName: string) {
  const source = `
from sqlalchemy import select
from app.core.database import get_session_factory
from app.models.enums import UserStatus
from app.models.identity import Role, User, UserRole

with get_session_factory()() as session, session.begin():
    role = session.scalar(select(Role).where(Role.code == "DOCTOR", Role.is_active.is_(True)))
    if role is None:
        raise RuntimeError("Active DOCTOR role is required")
    user = User(
        email=${JSON.stringify(email)},
        password_hash="!e2e-candidate-no-login",
        full_name=${JSON.stringify(fullName)},
        phone="0923456789",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=None))
`
  execFileSync(path.join(backendRoot, '.venv', 'Scripts', 'python.exe'), ['-c', source], {
    cwd: backendRoot,
    stdio: 'pipe',
  })
}

test('complete non-AI business workflow through the real UI', async ({ page }) => {
  test.skip(!adminPassword || !staffPassword, 'E2E_ADMIN_PASSWORD and E2E_STAFF_PASSWORD are required')
  test.setTimeout(240_000)

  const runId = Date.now().toString()
  const specialtyCode = `WF_${runId}`
  const specialtyName = `Chuyên khoa kiểm thử ${runId}`
  const specialtyNameUpdated = `${specialtyName} cập nhật`
  const doctorName = `BS Workflow ${runId}`
  const doctorEmail = `workflow.doctor.${runId}@example.invalid`
  const doctorPassword = `Dr${runId}a9!`
  const doctorLicense = `WF-GP-${runId}`
  const patientName = `Patient Workflow ${runId}`
  const patientEmail = `workflow.patient.${runId}@example.invalid`
  const patientPassword = `Pt${runId}b8!`
  const conclusion = `Kết luận synthetic ${runId}`
  const candidateName = `BS Candidate ${runId}`
  const candidateEmail = `workflow.candidate.${runId}@example.invalid`
  prepareDoctorCandidate(candidateEmail, candidateName)

  // ADMIN: real cookie login and Specialty create/edit/status workflow.
  await login(page, adminEmail, adminPassword!)
  await page.goto('/admin/specialties')
  await expect(page.getByRole('heading', { name: 'Quản lý chuyên khoa' })).toBeVisible()
  await page.getByRole('button', { name: 'Thêm chuyên khoa' }).click()
  let dialog = page.getByRole('dialog')
  await dialog.getByLabel('Mã chuyên khoa').fill(specialtyCode)
  await dialog.getByLabel('Tên chuyên khoa').fill(specialtyName)
  await dialog.getByLabel('Mô tả').fill('Dữ liệu synthetic cho kiểm chứng workflow sau Phase 14.')
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText(specialtyName)).toBeVisible()

  let specialtyCard = page.locator('.MuiCard-root').filter({ hasText: specialtyName }).first()
  await specialtyCard.getByRole('button', { name: 'Chỉnh sửa' }).click()
  dialog = page.getByRole('dialog')
  await dialog.getByLabel('Tên chuyên khoa').fill(specialtyNameUpdated)
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  specialtyCard = page.locator('.MuiCard-root').filter({ hasText: specialtyNameUpdated }).first()
  await expect(specialtyCard).toBeVisible()
  await specialtyCard.getByRole('switch').click()
  await expect(specialtyCard.getByText('Đã tắt')).toBeVisible()
  await specialtyCard.getByRole('switch').click()
  await expect(specialtyCard.getByText('Đang hoạt động')).toBeVisible()

  // ISSUE-001: link a prepared ACTIVE DOCTOR candidate through UI without a raw UUID.
  await page.goto('/admin/doctors')
  await page.getByRole('button', { name: 'Thêm bác sĩ' }).click()
  dialog = page.getByRole('dialog')
  await selectMuiOption(page, dialog, 'Tài khoản', 'Dùng tài khoản bác sĩ có sẵn')
  await expect(dialog.getByLabel('User UUID')).toHaveCount(0)
  await expect(dialog.getByRole('combobox', { name: 'Tài khoản bác sĩ' })).toBeVisible()
  await selectMuiOption(page, dialog, 'Tài khoản bác sĩ', `${candidateName} — ${candidateEmail}`)
  await selectMuiOption(page, dialog, 'Chuyên khoa', specialtyNameUpdated)
  await dialog.getByLabel('Số giấy phép').fill(`WF-CAND-${runId}`)
  await dialog.getByLabel('Giới thiệu').fill('Candidate synthetic được liên kết bằng tên và email.')
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText(candidateName)).toBeVisible()

  // Candidate disappears immediately after profile creation.
  await page.getByRole('button', { name: 'Thêm bác sĩ' }).click()
  dialog = page.getByRole('dialog')
  await selectMuiOption(page, dialog, 'Tài khoản', 'Dùng tài khoản bác sĩ có sẵn')
  await expect(dialog.getByText(candidateEmail)).toHaveCount(0)

  // ENH-001: provision User + DOCTOR role + Doctor profile through one Dialog.
  await selectMuiOption(page, dialog, 'Tài khoản', 'Tạo tài khoản bác sĩ mới')
  await dialog.getByLabel('Họ và tên').fill(doctorName)
  await dialog.getByLabel('Email').fill(doctorEmail)
  await dialog.getByLabel('Số điện thoại').fill('0901234567')
  await dialog.getByLabel('Mật khẩu tạm thời').fill(doctorPassword)
  await dialog.getByLabel('Xác nhận mật khẩu').fill(doctorPassword)
  await selectMuiOption(page, dialog, 'Chuyên khoa', specialtyNameUpdated)
  await dialog.getByLabel('Số giấy phép').fill(doctorLicense)
  await dialog.getByLabel('Giới thiệu').fill('Doctor synthetic được tạo hoàn toàn từ giao diện Admin.')
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText(doctorName)).toBeVisible()
  await page.reload()
  await expect(page.getByText(doctorName)).toBeVisible()
  await logout(page)

  // DOCTOR: login, role boundary, create/update Schedule, generate and block a slot.
  await login(page, doctorEmail, doctorPassword)
  await page.goto('/admin/doctors')
  await expect(page.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeVisible()
  await page.goto('/doctor/schedules')
  await expect(page.getByRole('heading', { name: 'Lịch làm việc', exact: true })).toBeVisible()

  const start = new Date()
  start.setDate(start.getDate() + 7)
  start.setHours(9, 0, 0, 0)
  const end = new Date(start)
  end.setHours(10, 0, 0, 0)
  const updatedEnd = new Date(start)
  updatedEnd.setHours(10, 30, 0, 0)

  await page.getByRole('button', { name: 'Tạo lịch' }).click()
  dialog = page.getByRole('dialog')
  await dialog.getByLabel('Bắt đầu').fill(localDateTimeValue(start))
  await dialog.getByLabel('Kết thúc').fill(localDateTimeValue(end))
  await dialog.getByLabel('Thời lượng mỗi khung giờ (phút)').fill('30')
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText('30 phút/khung giờ')).toBeVisible()

  await page.getByRole('button', { name: 'Chỉnh sửa lịch' }).click()
  dialog = page.getByRole('dialog')
  await dialog.getByLabel('Kết thúc').fill(localDateTimeValue(updatedEnd))
  await dialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText('30 phút/khung giờ')).toBeVisible()

  await page.getByRole('button', { name: 'Tạo khung giờ' }).click()
  await expect(page.getByText('Còn trống')).toHaveCount(3)
  await page.getByRole('button', { name: 'Chặn' }).first().click()
  await expect(page.getByRole('button', { name: 'Mở lại' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: 'Mở lại' })).toBeVisible()
  await expect(page.getByText('Còn trống')).toHaveCount(2)
  await logout(page)

  // PATIENT: register via UI, discover the new Doctor, book, cancel and rebook.
  await page.goto('/register')
  await page.getByLabel('Họ và tên').fill(patientName)
  await page.getByLabel('Số điện thoại').fill('0912345678')
  await page.getByLabel('Email').fill(patientEmail)
  await page.getByLabel('Mật khẩu').fill(patientPassword)
  await page.getByRole('button', { name: 'Tạo tài khoản' }).click()
  await expect(page.getByText(patientName)).toBeVisible()
  expect(await page.evaluate(() => ({ access: localStorage.getItem('access_token'), refresh: localStorage.getItem('refresh_token') })))
    .toEqual({ access: null, refresh: null })

  const selectDiscovery = async () => {
    await page.goto('/booking')
    await selectMuiOption(page, page, 'Chuyên khoa', specialtyNameUpdated)
    await selectMuiOption(page, page, 'Bác sĩ', doctorName)
    await expect(page.getByRole('button', { name: 'Chọn khung giờ' })).toHaveCount(2)
  }
  const bookFirstAvailable = async () => {
    await page.getByRole('button', { name: 'Chọn khung giờ' }).first().click()
    await page.getByLabel('Tôi đã kiểm tra khung giờ và xác nhận đặt lịch.').check()
    await page.getByRole('button', { name: 'Xác nhận đặt lịch' }).click()
    await expect(page.getByText('Đặt lịch thành công. Bạn có thể xem lại trong mục Lịch hẹn của tôi.')).toBeVisible()
  }

  await selectDiscovery()
  await bookFirstAvailable()
  await page.goto('/appointments')
  await expect(page.getByText('Đã xác nhận', { exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Hủy lịch' }).click()
  dialog = page.getByRole('dialog')
  await dialog.getByLabel('Lý do hủy').fill('Kiểm chứng luồng hủy và đặt lại synthetic.')
  await dialog.getByRole('button', { name: 'Xác nhận hủy' }).click()
  await expect(page.getByText('Đã hủy', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Đã hủy', { exact: true })).toBeVisible()

  await selectDiscovery()
  await bookFirstAvailable()
  await page.goto('/appointments')
  await expect(page.getByText('Đã hủy', { exact: true })).toBeVisible()
  await expect(page.getByText('Đã xác nhận', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Đã xác nhận', { exact: true })).toBeVisible()
  await logout(page)

  // DOCTOR: complete the rebooked Appointment and create a MedicalRecord through UI.
  await login(page, doctorEmail, doctorPassword)
  await page.goto('/doctor/appointments')
  await expect(page.getByText('Đã xác nhận', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Đã khám' }).click()
  await expect(page.getByText('Đã cập nhật kết quả lịch hẹn.')).toBeVisible()
  await expect(page.getByText('Đã khám', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Hồ sơ khám' }).click()
  await page.getByLabel('Triệu chứng ghi nhận').fill(`Triệu chứng synthetic ${runId}`)
  await page.getByLabel('Ghi chú khám').fill(`Ghi chú synthetic ${runId}`)
  await page.getByLabel('Kết luận do bác sĩ nhập').fill(conclusion)
  await page.getByLabel('Hướng dẫn sau khám').fill(`Hướng dẫn synthetic ${runId}`)
  await page.getByRole('button', { name: 'Tạo hồ sơ khám' }).click()
  await expect(page.getByText('Hồ sơ khám đã được lưu thành công.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Lưu cập nhật' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Cập nhật hồ sơ khám' })).toBeVisible()
  await logout(page)

  // PATIENT: restore persisted state and read the MedicalRecord without edit/delete controls.
  await login(page, patientEmail, patientPassword)
  await page.goto('/medical-history')
  await expect(page.getByText(conclusion)).toBeVisible()
  await page.getByRole('link', { name: 'Xem chi tiết' }).click()
  await expect(page.getByText(`Triệu chứng synthetic ${runId}`)).toBeVisible()
  await expect(page.getByText(conclusion)).toBeVisible()
  await expect(page.getByRole('button', { name: /Lưu|Cập nhật|Xóa/ })).toHaveCount(0)
  const recordPath = new URL(page.url()).pathname
  await page.reload()
  await expect(page.getByText(conclusion)).toBeVisible()
  await page.goto('/admin/doctors')
  await expect(page.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeVisible()
  await logout(page)

  // STAFF/ADMIN: business routes work, clinical route remains denied by role guard.
  await login(page, staffEmail, staffPassword!)
  await page.goto('/admin/documents')
  await expect(page.getByRole('heading', { name: 'Tài liệu tri thức', exact: true })).toBeVisible()
  await page.goto('/handoffs')
  await expect(page.getByRole('heading', { name: 'Yêu cầu hỗ trợ' })).toBeVisible()
  await page.goto(recordPath)
  await expect(page.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeVisible()
  await logout(page)

  await login(page, adminEmail, adminPassword!)
  await page.goto(recordPath)
  await expect(page.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeVisible()
  await logout(page)
})
