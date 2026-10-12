import { defineConfig } from 'vite';

export default defineConfig({
  build: { outDir: '../vidhaan/web', emptyOutDir: true, sourcemap: false },
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
});
