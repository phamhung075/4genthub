/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const parentDir = path.resolve(__dirname, '..')
  const envDevPath = path.join(parentDir, '.env.dev')
  const envPath = path.join(parentDir, '.env')

  // Check which env file exists
  const hasEnvDev = fs.existsSync(envDevPath)
  const hasEnv = fs.existsSync(envPath)

  // INTENTIONAL: Using console.log in vite.config.ts (build-time configuration)
  // This file runs in Node.js during build, not in browser where logger is available
  // Logger cannot be imported here as it depends on browser APIs and Vite environment

  // Log which file will be used - Priority: .env.dev > .env
  if (hasEnvDev) {
    if (hasEnv) {
      console.log('📁 Both .env and .env.dev exist, using .env.dev priority')
    } else {
      console.log('📁 Using .env.dev (no .env file found)')
    }
    // Only copy if contents are different to avoid infinite restart loop
    if (hasEnv) {
      const envContent = fs.readFileSync(envPath, 'utf8')
      const envDevContent = fs.readFileSync(envDevPath, 'utf8')
      if (envContent !== envDevContent) {
        console.log('📁 Copying .env.dev to .env (contents differ)')
        fs.copyFileSync(envDevPath, envPath)
      }
    } else {
      console.log('📁 Copying .env.dev to .env (no .env exists)')
      fs.copyFileSync(envDevPath, envPath)
    }
  } else if (hasEnv) {
    console.log('📁 Using existing .env file (no .env.dev found)')
  } else {
    console.log('⚠️  No .env or .env.dev file found in parent directory')
  }

  // Load env file from parent directory (Vite will look for .env)
  const env = loadEnv(mode, parentDir, '')

  return {
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3800,
    hmr: {
      protocol: 'ws',
      host: '0.0.0.0',
      port: 3800,
      clientPort: 3800
    },
    watch: {
      usePolling: true,
      interval: 100,
      binaryInterval: 300,
      awaitWriteFinish: {
        stabilityThreshold: 500,
        pollInterval: 100
      }
    },
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    },
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json']
  },
  build: {
    outDir: 'build'
  },
  define: {
    // Fix for React 19 compatibility
    global: 'globalThis'
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    css: true
  },
  envDir: '..' // Load .env from parent directory
  }
})