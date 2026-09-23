import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  base: './',
  esbuild: { jsxFactory: 'h', jsxFragment: 'Fragment' },
  resolve: { alias: { '!../css/base.css': resolve('node_modules/@create-figma-plugin/ui/lib/css/base.css') } },
  build: { outDir: 'dist', emptyOutDir: true },
})
