import { defineConfig } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.dirname(fileURLToPath(import.meta.url))
const backendRoot = path.resolve(frontendRoot, '..', 'healthcare-backend')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5174',
    channel: 'msedge',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: '.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host localhost --port 8013',
      cwd: backendRoot,
      url: 'http://localhost:8013/api/v1/health',
      env: {
        ...process.env,
        FRONTEND_ORIGIN: 'http://localhost:5174',
        DEV_AUTH_ENABLED: 'false',
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm.cmd exec vite -- --host localhost --port 5174 --strictPort',
      cwd: frontendRoot,
      url: 'http://localhost:5174',
      env: {
        ...process.env,
        VITE_API_BASE_URL: 'http://localhost:8013/api/v1',
        VITE_ENABLE_DEV_AUTH: 'false',
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
