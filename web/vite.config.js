import { defineConfig } from 'vite';

// Settings below are required by @surrealdb/wasm, per SurrealDB's own docs:
// https://surrealdb.com/docs/sdk/javascript/engines/wasm
export default defineConfig({
  server: {
    proxy: {
      '/convert': 'http://localhost:7860',
      '/suggest': 'http://localhost:7860',
      '/health': 'http://localhost:7860',
    }
  },
  optimizeDeps: {
    exclude: ['@surrealdb/wasm'],
    esbuildOptions: {
      target: 'esnext',
    },
  },
  esbuild: {
    supported: {
      'top-level-await': true,
    },
  },
  // Relative base works from both GitLab and GitHub project Pages subpaths.
  base: './',
  build: {
    outDir: 'dist',
  },
});
