/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { visualizer } from 'rollup-plugin-visualizer'

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
  loadEnv(mode, parentDir, '')

  // HMR Debug Plugin
  const hmrDebugPlugin = {
    name: 'hmr-debug',
    handleHotUpdate({ file, server, modules }: any) {
      const timestamp = new Date().toISOString()
      console.log(`\n🔥 [${timestamp}] HMR Update Triggered`)
      console.log(`   📄 File: ${file}`)
      console.log(`   🔗 Modules affected: ${modules?.length || 0}`)

      // Log file-based modules
      const fileModules = server.moduleGraph.getModulesByFile(file)
      console.log(`   📊 File modules in graph: ${fileModules?.size || 0}`)

      if (modules && modules.length > 0) {
        modules.forEach((mod: any, index: number) => {
          console.log(`   ↳ Module ${index + 1}: ${mod.id || mod.url}`)
          console.log(`      Type: ${mod.type || 'unknown'}`)
          console.log(`      Importers: ${mod.importers?.size || 0}`)
          console.log(`      Imported: ${mod.importedModules?.size || 0}`)

          if (mod.importers && mod.importers.size > 0) {
            const importersList = Array.from(mod.importers)
              .slice(0, 3)
              .map((imp: any) => imp.id || imp.url)
            console.log(`      ⤷ Imported by: ${importersList.join(', ')}`)
          }
        })
      } else {
        console.log(`   ⚠️  No modules returned - HMR may not work!`)
        console.log(`   💡 This usually means:`)
        console.log(`      1. File isn't imported anywhere`)
        console.log(`      2. Module graph hasn't loaded this file yet`)
        console.log(`      3. File pattern doesn't match plugin includes`)
      }

      return undefined // Let Vite handle the update normally
    },
    configureServer(server: any) {
      console.log('\n🚀 HMR Debug Plugin Enabled')
      console.log('   Watching for file changes...\n')

      // Log when HMR connection is established
      server.ws.on('connection', () => {
        console.log('🔌 HMR WebSocket connection established')
      })

      // Log HMR errors
      server.ws.on('error', (error: any) => {
        console.error('❌ HMR WebSocket error:', error)
      })
    }
  }

  return {
  plugins: [
    react(),
    hmrDebugPlugin,
    // Bundle analyzer - generates stats.html after build
    visualizer({
      filename: './build/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    })
  ],
  server: {
    host: '0.0.0.0',
    port: 3800,
    hmr: {
      protocol: 'ws',
      host: 'localhost',
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
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json', '.css']
  },
  build: {
    outDir: 'build',
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate vendor chunks for better caching
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': [
            '@radix-ui/react-accordion',
            '@radix-ui/react-collapsible',
            '@radix-ui/react-separator',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
          ],
          'mui-vendor': [
            '@mui/material',
            '@mui/icons-material',
            '@emotion/react',
            '@emotion/styled',
          ],
          'state-vendor': ['zustand'],
          'animation-vendor': ['framer-motion'],
          'utils-vendor': ['date-fns', 'clsx', 'tailwind-merge', 'class-variance-authority'],
        },
      },
    },
    // Increase chunk size warning limit since we're splitting intentionally
    chunkSizeWarningLimit: 600,
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