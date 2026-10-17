import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  retries: 0,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 1050 },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "python -m uvicorn worker.main:app --port 8001",
      cwd: "..",
      url: "http://127.0.0.1:8001/openapi.json",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command:
        "python -m alembic upgrade head && python -m uvicorn backend.app.main:app --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      env: { ACE_DATABASE_URL: "sqlite:///./e2e.db" },
      timeout: 30000,
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
