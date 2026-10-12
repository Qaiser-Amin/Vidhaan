import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const browserPath = process.env.CHROMIUM_PATH || (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
const port = 8796;
export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, timeout: 30000,
  reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
  use: { baseURL: `http://127.0.0.1:${port}`, viewport: { width: 1440, height: 1000 },
    launchOptions: { executablePath: browserPath }, trace: 'retain-on-failure' },
  webServer: {
    command: `cd .. && .venv/bin/python -m vidhaan.cli load-bundled && .venv/bin/python app.py --port ${port}`,
    url: `http://127.0.0.1:${port}/api/health`, reuseExistingServer: false, timeout: 120000,
    env: { VIDHAAN_DATA_DIR: join(tmpdir(), `vidhaan-web-tests-${process.pid}`), VIDHAAN_PROFILE: 'evidence_only' },
  },
});
