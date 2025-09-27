#!/usr/bin/env node

/**
 * DEBUG SCRIPT: Environment Variable Test
 * Purpose: Check what environment variables are actually loaded by the frontend
 */

console.log('🔍 ENVIRONMENT VARIABLE DEBUG TEST');
console.log('=====================================');

// Test if we can access the environment variables the same way Vite does
const fs = require('fs');
const path = require('path');

const projectRoot = '/home/daihungpham/__projects__/4genthub';
const envPath = path.join(projectRoot, '.env');
const envDevPath = path.join(projectRoot, '.env.dev');

console.log('\n📁 ENVIRONMENT FILE STATUS:');
console.log(`   .env exists: ${fs.existsSync(envPath)}`);
console.log(`   .env.dev exists: ${fs.existsSync(envDevPath)}`);

// Check which file Vite would prioritize
if (fs.existsSync(envDevPath)) {
  console.log('   Priority: .env.dev (higher priority)');
} else if (fs.existsSync(envPath)) {
  console.log('   Priority: .env (only file available)');
} else {
  console.log('   ❌ No environment files found!');
}

console.log('\n🔍 CURRENT PROCESS ENVIRONMENT:');
console.log(`   VITE_WS_URL: "${process.env.VITE_WS_URL || 'NOT SET'}"`);
console.log(`   NODE_ENV: "${process.env.NODE_ENV || 'NOT SET'}"`);

// Test environment loading similar to Vite
console.log('\n🧪 SIMULATING VITE ENV LOADING:');

// Since we can't read .env files directly (security), let's grep for the variable
try {
  const { execSync } = require('child_process');

  console.log('   Checking .env.dev for VITE_WS_URL:');
  try {
    const result = execSync(`grep -n "VITE_WS_URL" "${envDevPath}" 2>/dev/null || echo "NOT FOUND"`, { encoding: 'utf8' });
    console.log(`     Result: ${result.trim()}`);
  } catch (error) {
    console.log('     Result: .env.dev not accessible or VITE_WS_URL not found');
  }

  console.log('   Checking .env for VITE_WS_URL:');
  try {
    const result = execSync(`grep -n "VITE_WS_URL" "${envPath}" 2>/dev/null || echo "NOT FOUND"`, { encoding: 'utf8' });
    console.log(`     Result: ${result.trim()}`);
  } catch (error) {
    console.log('     Result: .env not accessible or VITE_WS_URL not found');
  }

} catch (error) {
  console.log('   ❌ Cannot execute grep commands:', error.message);
}

console.log('\n✅ Debug test completed!');