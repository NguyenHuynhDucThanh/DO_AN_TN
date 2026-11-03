import { expect, test } from '@playwright/test'

test('public business discovery and Backend health work end to end', async ({ page, request }) => {
  const health = await request.get('http://localhost:8013/api/v1/health')
  expect(health.ok()).toBeTruthy()
  expect(await health.json()).toMatchObject({ status: 'ok' })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Chăm sóc sức khỏe bắt đầu từ thông tin rõ ràng.' })).toBeVisible()

  await page.goto('/specialties')
  await expect(page.getByRole('heading', { name: 'Chuyên khoa' })).toBeVisible()
  await expect(page.getByText('Tai Mũi Họng').first()).toBeVisible()

  await page.goto('/doctors')
  await expect(page.getByRole('heading', { name: 'Bác sĩ' })).toBeVisible()
  await expect(page.getByText('BS. Nguyễn Minh An (Demo)').first()).toBeVisible()
})

test('protected route redirects to login without exposing tokens', async ({ page }) => {
  await page.goto('/appointments')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Đăng nhập' })).toBeVisible()
  const tokenState = await page.evaluate(() => ({
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  }))
  expect(tokenState).toEqual({ access: null, refresh: null })
})

test('registration validation prevents malformed submission in the browser', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('Họ và tên').fill('A')
  await page.getByLabel('Số điện thoại').fill('12')
  await page.getByLabel('Email').fill('phase13@example.invalid')
  await page.getByLabel('Mật khẩu').fill('weak')
  await page.getByRole('button', { name: 'Tạo tài khoản' }).click()
  await expect(page.getByText('Họ tên cần ít nhất 2 ký tự.')).toBeVisible()
  await expect(page.getByText('Số điện thoại là bắt buộc.')).toBeVisible()
  await expect(page).toHaveURL(/\/register$/)
})
