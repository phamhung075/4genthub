/**
 * Subscription Debugger Utility
 *
 * Add this to window for debugging subscription memory leaks
 * Usage in browser console: window.debugSubscriptions()
 */

import { changePoolService } from '../services/changePoolService';

export function debugSubscriptions() {
  console.log('=== ChangePool Subscription Debugger ===');

  // Get current stats
  const stats = changePoolService.getSubscriptionStats();

  console.log(`📊 Total Subscriptions: ${stats.total}`);

  if (stats.total === 0) {
    console.log('✅ No subscriptions found (good if no components are mounted)');
    return;
  }

  console.log('\n📋 Subscriptions by Component:');
  Object.entries(stats.byComponent).forEach(([componentId, info]) => {
    console.log(`  • ${componentId}: [${info.entityTypes.join(', ')}]${info.hasFilters ? ' (filtered)' : ''}`);
  });

  console.log('\n📈 Subscriptions by Entity Type:');
  Object.entries(stats.byEntityType).forEach(([entityType, count]) => {
    const status = count > 3 ? '⚠️' : '✅';
    console.log(`  ${status} ${entityType}: ${count}`);
  });

  if (stats.potentialDuplicates.length > 0) {
    console.log('\n⚠️ Potential Duplicate Component Patterns:');
    stats.potentialDuplicates.forEach(pattern => {
      console.log(`  • ${pattern} (may indicate components not cleaning up properly)`);
    });
  }

  // Health assessment
  console.log('\n🏥 Health Assessment:');
  if (stats.total <= 3) {
    console.log('✅ Healthy: Low subscription count');
  } else if (stats.total <= 10) {
    console.log('⚠️ Moderate: Consider checking for unnecessary subscriptions');
  } else {
    console.log('🚨 High: Likely memory leak - components not unsubscribing properly');
  }

  // Recommendations
  if (stats.total > 5) {
    console.log('\n💡 Recommendations:');
    console.log('  • Check that components properly cleanup subscriptions on unmount');
    console.log('  • Verify useEffect dependency arrays are stable');
    console.log('  • Look for components re-mounting unnecessarily');
  }

  console.log('\n🔧 Advanced Debug Commands:');
  console.log('  changePoolService.debugSubscriptions() - Detailed debug info');
  console.log('  changePoolService.clearAllSubscriptions() - Clear all (use carefully!)');
}

// Auto-expose to window in development
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  (window as any).debugSubscriptions = debugSubscriptions;
  (window as any).changePoolService = changePoolService;

  console.log('🔧 Subscription debugger available: window.debugSubscriptions()');
}