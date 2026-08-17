import { defineConfig } from 'vite';

// Settings below are required by @surrealdb/wasm, per SurrealDB's own docs:
// https://surrealdb.com/docs/sdk/javascript/engines/wasm
export default defineConfig({
  server: {
    proxy: {
      '/convert': 'http://localhost:7860',
      '/suggest': 'http://localhost:7860',
      '/health': 'http://localhost:7860',
      '/data': 'http://localhost:7860',
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
  // Relative base so the build works when served from a GitLab Pages
  // subpath (e.g. https://<user>.codebase.helmholtz.cloud/<project>/),
  // not just from a domain root.
  base: './',
  build: {
    outDir: 'dist',
  },
});
