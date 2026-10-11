/// <reference types="vitest" />
import { defineConfig, loadEnv, type Plugin } from 'vite'
import { configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { visualizer } from 'rollup-plugin-visualizer'
import { describeArtefact, MINIFIED_BYTES_PER_LINE_FLOOR } from './src/config/artefactReport'

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

  // PROMISE: .env.dev > .env, BY DESIGN - DECLARED here, and NEVER applied by copying one file
  // over the other. The copy this replaces rewrote the parent's .env (which holds DATABASE_*,
  // SUPABASE_*, JWT_SECRET_KEY) on EVERY config load - vite build, the dev server and every
  // vitest run - so one seat's run could rewrite the file another seat's run reads, and the
  // tree was not byte-stable across a build.
  //
  // Vite only reads .env, .env.local, .env.<mode> and .env.<mode>.local from envDir, so the
  // priority is taken from Vite's OWN loader at mode 'dev': loadEnv('dev', parentDir) reads
  // .env, .env.local, .env.dev and .env.dev.local in Vite's documented order, which places
  // .env.dev above .env. Seeding that into process.env is what makes it win: Vite's loadEnv
  // copies process.env over the file values once the files are read (the second loop in
  // vite/dist/node .../env.ts), so a value from the .env.dev chain outranks the parent's .env.
  // Only NODE_ENV and VITE_* are seeded: NODE_ENV because it decides the build mode, VITE_*
  // because they reach the client - the rest of the file's secrets are not promoted into the
  // build process's environment. A value already set in the real environment is left alone,
  // so `VITE_API_URL=... npx vite build` still wins.
  if (hasEnvDev) {
    console.log(
      hasEnv
        ? `📁 mode "${mode}": .env.dev wins over .env (declared, not copied)`
        : `📁 mode "${mode}": using .env.dev (no .env file found)`
    )
    for (const [key, value] of Object.entries(loadEnv('dev', parentDir, ''))) {
      if ((key.startsWith('VITE_') || key === 'NODE_ENV') && process.env[key] === undefined) {
        process.env[key] = value
      }
    }
  } else if (hasEnv) {
    console.log('📁 Using existing .env file (no .env.dev found)')
  } else {
    console.log('⚠️  No .env or .env.dev file found in parent directory')
  }

  // WHAT THE BUILD RESOLVED AND WHAT IT PRODUCED, printed by the build itself (row 2dd4448e).
  //
  // TWO INDEPENDENT AXES, EACH WITH A CONFIGURED CAUSE AND AN OBSERVED EFFECT. The mistake this block
  // exists to stop is printing one as though it described the other:
  //
  //   REACT RESOLUTION  cause: NODE_ENV, which decides which React the bundle carries. Observed from
  //                     the `Minified React error` marker, which only the production React build
  //                     contains - present in the deployed entry (301,330 B / 39 newlines) and in the
  //                     production-React build that is unminified (758,581 B / 18,313), absent here.
  //   MINIFICATION      cause: `build.minify`, NOT NODE_ENV - Vite defaults it to 'esbuild' and
  //                     nothing in this config sets it, so BOTH families are minified. Observed as
  //                     MEAN bytes per line against MINIFIED_BYTES_PER_LINE_FLOOR. The retired
  //                     100-newline threshold was the wrong instrument for this axis: 245 newlines IS
  //                     the minified reading for development React, so it confirmed the false
  //                     `unminified` label instead of catching it.
  //
  // The entry chunk's NAME cannot answer either axis: it survived a comment-only edit where no parent
  // .env existed, it moved on a +0.7% byte change, and it moved at an IDENTICAL byte size in this
  // tree. The line above logs Vite's MODE, always "production" for `vite build`, which is neither axis.
  //
  // describeArtefact (src/config/artefactReport.ts) is the pure form of both axes, so every cell and
  // both mismatch directions are pinned by tests instead of by a build.
  let configuredMinify: boolean | 'terser' | 'esbuild' | undefined
  const artefactReportPlugin: Plugin = {
    name: 'artefact-report',
    apply: 'build',
    configResolved(config) {
      // THE DECISION, read from the resolved config rather than inferred from NODE_ENV. Vite's own
      // @default is 'esbuild', so this reads the resolved lever (measured 'esbuild') and needs no fallback.
      configuredMinify = config.build.minify
    },
    closeBundle() {
      const outDir = path.resolve(__dirname, 'build')
      const entry = fs
        .readFileSync(path.join(outDir, 'index.html'), 'utf8')
        .match(/assets\/index-[\w-]+\.js/)?.[0]
      if (!entry) {
        console.log('\n📦 No entry chunk found in build/index.html - the artefact cannot be reported.')
        return
      }
      const entryPath = path.join(outDir, entry)
      const text = fs.readFileSync(entryPath, 'utf8')
      const report = describeArtefact({
        bytes: fs.statSync(entryPath).size,
        newlines: text.split('\n').length - 1,
        markerPresent: text.includes('Minified React error'),
        nodeEnv: process.env.NODE_ENV,
        configuredMinify
      })
      console.log('\n📦 THE ARTEFACT THIS BUILD PRODUCED')
      console.log(`   entry      ${entry}`)
      console.log(
        `   size       ${report.bytes} B   newlines ${report.newlines}   bytes/line ${report.bytesPerLine.toFixed(1)}`
      )
      console.log(
        `   react      ${report.reactObserved} (observed: 'Minified React error' ${report.markerPresent ? 'present' : 'absent'})   cause: NODE_ENV ${process.env.NODE_ENV}`
      )
      console.log(
        `   minified   ${report.observedMinified ? 'yes' : 'no'} (observed: ${report.bytesPerLine.toFixed(1)} bytes/line vs floor ${MINIFIED_BYTES_PER_LINE_FLOOR})   cause: build.minify ${String(configuredMinify)}`
      )
      console.log(`   family     ${report.familyLabel}`)
      for (const mismatch of report.mismatches) {
        console.log(`   ⚠  SIGNATURE MISMATCH: ${mismatch}`)
      }
      if (!report.isDeployShape) {
        console.log('   ⚠  NOT the deploy artefact: the frontend image builds PRODUCTION React, minified (about 299 kB / 39 newlines,')
        console.log('      and no parent .env exists inside it). NODE_ENV=production in the process environment builds it here.')
      }
    }
  }

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
    artefactReportPlugin,
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
      '/api': 'http://localhost:8000',
      // The realtime socket lives on the API origin, and the app derives its URL from the page origin in
      // development (config/environment.ts). Without this entry the socket went to the DEV SERVER itself,
      // whose own websocket server accepts the upgrade, so the app reported Live with nothing behind it.
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
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
    css: true,
    // Bounded on purpose: this box also runs the agent seats, and an uncapped run spawns one
    // jsdom worker per CPU (12 here). Four runaway workers starved the machine on 2026-10-05.
    // Override per run when the box is free: npx vitest run --maxWorkers=6
    maxWorkers: 2,
    minWorkers: 1,
    // VITEST 4 REMOVED `poolOptions` and made its keys TOP-LEVEL options, which the run
    // says out loud ("Deprecated: test.poolOptions was removed in Vitest 4"). The fork's
    // heap cap therefore lives here now; leaving it nested would be a silently ignored
    // option, the same shape as the override that used to be ignored in package.json.
    execArgv: ['--max-old-space-size=2048'],
    // Playwright spec; the repo has no Playwright config, so vitest must not collect it
    exclude: [...configDefaults.exclude, 'src/tests/e2e/live-websocket.test.ts']
  },
  envDir: '..' // Load .env from parent directory
  }
})
