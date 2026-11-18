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
  await expect(page.getByText('Đăng nhập', { exact: true }).first()).toBeVisible()
}

async function selectMuiOption(page: Page, scope: Page | Locator, label: string, option: string) {
  await scope.getByRole('combobox', { name: label, exact: true }).click()
  await page.getByRole('option', { name: option, exact: true }).click()
}

function verifyRetrieval(title: string, marker: string, expected: boolean) {
  const source = `
from sqlalchemy import select
from app.core.database import get_session_factory
from app.models.knowledge import Document, EMBEDDING_DIMENSION
from app.rag.retrieval import ExactDenseRetriever

with get_session_factory()() as session:
    document = session.scalar(select(Document).where(Document.title == ${JSON.stringify(title)}))
    assert document is not None, "KB-001C document was not found"
    if ${expected ? 'True' : 'False'}:
        assert document.approval_status.value == "APPROVED"
        assert document.ingestion_status.value == "COMPLETED"
        assert document.chunks, "No chunks were created"
        query = list(document.chunks[0].embedding)
        results = ExactDenseRetriever(session, top_k=10, max_distance=0.001).retrieve(query)
        matches = [item for item in results if item.source.document_id == document.id]
        assert matches, "The ingested document was not retrieved"
        assert any(${JSON.stringify(marker)} in item.content for item in matches)
        assert matches[0].source.title == document.title
    else:
        assert document.approval_status.value == "APPROVED"
        assert document.ingestion_status.value == "NOT_INGESTED"
        results = ExactDenseRetriever(session, top_k=100, max_distance=2.0).retrieve([1.0] + [0.0] * (EMBEDDING_DIMENSION - 1))
        assert all(item.source.document_id != document.id for item in results)
`
  execFileSync(path.join(backendRoot, '.venv', 'Scripts', 'python.exe'), ['-c', source], {
    cwd: backendRoot,
    stdio: 'pipe',
  })
}

test('KB-001C Doctor contribution to Admin review, ingestion and retrieval', async ({ page }) => {
  test.skip(!adminPassword || !staffPassword, 'E2E_ADMIN_PASSWORD and E2E_STAFF_PASSWORD are required')
  test.setTimeout(600_000)

  const runId = Date.now().toString()
  const doctorName = `BS Tri thức ${runId}`
  const doctorEmail = `kb001c.doctor.${runId}@example.invalid`
  const doctorPassword = `KbDr${runId}a9!`
  const patientName = `Người bệnh KB ${runId}`
  const patientEmail = `kb001c.patient.${runId}@example.invalid`
  const patientPassword = `KbPt${runId}b8!`
  const title = `Tài liệu tri thức synthetic ${runId}`
  const marker = `NOI_DUNG_NHAN_DIEN_KB001C_${runId}`
  const rejectionReason = `Bổ sung mô tả nguồn synthetic ${runId}`

  // Bootstrap the Doctor account through the existing Admin UI, not through raw UUID/API/SQL.
  await login(page, adminEmail, adminPassword!)
  await page.goto('/admin/doctors')
  await page.getByRole('button', { name: 'Thêm bác sĩ' }).click()
  const doctorDialog = page.getByRole('dialog')
  await selectMuiOption(page, doctorDialog, 'Tài khoản', 'Tạo tài khoản bác sĩ mới')
  await doctorDialog.getByLabel('Họ và tên').fill(doctorName)
  await doctorDialog.getByLabel('Email').fill(doctorEmail)
  await doctorDialog.getByLabel('Số điện thoại').fill('0901234567')
  await doctorDialog.getByLabel('Mật khẩu tạm thời').fill(doctorPassword)
  await doctorDialog.getByLabel('Xác nhận mật khẩu').fill(doctorPassword)
  await selectMuiOption(page, doctorDialog, 'Chuyên khoa', 'Nội tổng quát')
  await doctorDialog.getByLabel('Số giấy phép').fill(`KB-CCHN-${runId}`)
  await doctorDialog.getByLabel('Giới thiệu').fill('Bác sĩ synthetic phục vụ kiểm thử đóng góp tri thức.')
  await doctorDialog.getByRole('button', { name: 'Lưu' }).click()
  await expect(page.getByText(doctorName)).toBeVisible()
  await logout(page)

  // Doctor uploads through UI and sees only the safe own-contribution view.
  await login(page, doctorEmail, doctorPassword)
  await expect(page.getByRole('link', { name: 'Tài liệu đóng góp' })).toBeVisible()
  await page.getByRole('link', { name: 'Tài liệu đóng góp' }).click()
  await page.getByRole('button', { name: 'Đóng góp tài liệu' }).click()
  const uploadDialog = page.getByRole('dialog')
  await uploadDialog.locator('input[type="file"]').setInputFiles({
    name: `kb001c-${runId}.json`,
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({ title, content: `${marker} Nội dung y khoa công khai tổng hợp để kiểm thử.` })),
  })
  await uploadDialog.getByLabel('Tiêu đề').fill(title)
  await uploadDialog.getByRole('textbox', { name: 'Nguồn', exact: true }).fill('Nguồn synthetic công khai')
  await uploadDialog.getByLabel('Tác giả').fill(doctorName)
  await uploadDialog.getByLabel('Tổ chức').fill('Cơ sở kiểm thử đồ án')
  await uploadDialog.getByLabel('Năm xuất bản').fill('2026')
  await uploadDialog.getByRole('button', { name: 'Gửi tài liệu' }).click()
  const doctorCard = page.locator('.MuiCard-root').filter({ hasText: title }).first()
  await expect(doctorCard.getByText('Chờ duyệt', { exact: true })).toBeVisible()
  await expect(doctorCard.getByText('Chưa xử lý', { exact: true })).toBeVisible()
  await expect(doctorCard.getByRole('button', { name: /Duyệt|Từ chối|kho tri thức/i })).toHaveCount(0)
  await expect(doctorCard.getByText(/storage_key|checksum_sha256/i)).toHaveCount(0)
  await logout(page)

  // Admin inspects the real file and rejects with a mandatory reason.
  await login(page, adminEmail, adminPassword!)
  await page.goto('/admin/documents')
  let adminCard = page.locator('.MuiCard-root').filter({ hasText: title }).first()
  await expect(adminCard).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await adminCard.getByRole('button', { name: 'Kiểm tra tệp' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe(`kb001c-${runId}.json`)
  await adminCard.getByRole('button', { name: 'Từ chối' }).click()
  const rejectDialog = page.getByRole('dialog')
  await rejectDialog.getByRole('button', { name: 'Xác nhận từ chối' }).click()
  await expect(rejectDialog.getByText('Hãy nhập lý do từ chối.')).toBeVisible()
  await rejectDialog.getByLabel('Lý do từ chối').fill(rejectionReason)
  await rejectDialog.getByRole('button', { name: 'Xác nhận từ chối' }).click()
  await expect(adminCard.getByText('Bị từ chối', { exact: true })).toBeVisible()
  await expect(adminCard.getByText(`Lý do từ chối: ${rejectionReason}`)).toBeVisible()
  await logout(page)

  // Doctor sees the reason, edits metadata and resubmits.
  await login(page, doctorEmail, doctorPassword)
  await page.goto('/doctor/contributions')
  await expect(doctorCard.getByText(`Lý do từ chối: ${rejectionReason}`)).toBeVisible()
  await doctorCard.getByRole('button', { name: 'Chỉnh sửa và gửi lại' }).click()
  const editDialog = page.getByRole('dialog')
  await editDialog.getByRole('textbox', { name: 'Nguồn', exact: true }).fill('Nguồn synthetic công khai đã bổ sung')
  await editDialog.getByRole('button', { name: 'Gửi lại' }).click()
  await expect(doctorCard.getByText('Chờ duyệt', { exact: true })).toBeVisible()
  await expect(doctorCard.getByText('Chưa xử lý', { exact: true })).toBeVisible()
  await logout(page)

  // Approval and ingestion stay separate. Before ingestion, retrieval must exclude the document.
  await login(page, adminEmail, adminPassword!)
  await page.goto('/admin/documents')
  adminCard = page.locator('.MuiCard-root').filter({ hasText: title }).first()
  await adminCard.getByRole('button', { name: 'Duyệt' }).click()
  await expect(adminCard.getByText('Đã duyệt', { exact: true })).toBeVisible()
  await expect(adminCard.getByText('Chưa xử lý', { exact: true })).toBeVisible()
  verifyRetrieval(title, marker, false)
  await adminCard.getByRole('button', { name: 'Đưa vào kho tri thức' }).click()
  await expect(adminCard.getByText('Đã đưa vào kho tri thức', { exact: true })).toBeVisible({ timeout: 300_000 })
  verifyRetrieval(title, marker, true)
  await logout(page)

  // Patient has neither corpus UI nor direct route access.
  await page.goto('/register')
  await page.getByLabel('Họ và tên').fill(patientName)
  await page.getByLabel('Số điện thoại').fill('0912345678')
  await page.getByLabel('Email').fill(patientEmail)
  await page.getByLabel('Mật khẩu').fill(patientPassword)
  await page.getByRole('button', { name: 'Tạo tài khoản' }).click()
  await expect(page.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
  await logout(page)
  await login(page, patientEmail, patientPassword)
  await expect(page.getByRole('link', { name: 'Tài liệu đóng góp' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Tài liệu tri thức' })).toHaveCount(0)
  await page.goto('/doctor/contributions')
  await expect(page.getByText('Tài khoản của bạn không có quyền truy cập màn hình này.')).toBeVisible()
  await logout(page)

  // Staff may inspect metadata but cannot review, download or ingest.
  await login(page, staffEmail, staffPassword!)
  await expect(page.getByRole('link', { name: 'Tài liệu đóng góp' })).toHaveCount(0)
  await page.goto('/admin/documents')
  const staffCard = page.locator('.MuiCard-root').filter({ hasText: title }).first()
  await expect(staffCard).toBeVisible()
  await expect(staffCard.getByRole('button', { name: /Kiểm tra tệp|Duyệt|Từ chối|kho tri thức/i })).toHaveCount(0)
})
