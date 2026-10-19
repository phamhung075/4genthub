/**
 * Branch Service - Optimized for Bulk API Usage
 *
 * This service provides a clean interface for branch summary operations
 * using the new bulk API endpoint. Replaces multiple API calls with
 * single optimized requests.
 */

import { branchApiV2 } from './apiV2';
import { BranchSummary, ProjectSummary, BulkSummaryResponse } from '../types/api.types';
import logger from '../utils/logger';
import { invalidateRequestCache, clearDeduplicationCache } from '../utils/requestDeduplication';

export class BranchService {
  /**
   * Load all summaries for current user
   * SINGLE API CALL ONLY - replaces multiple legacy calls
   */
  async loadUserSummaries(): Promise<{
    branches: BranchSummary[];
    projects: ProjectSummary[];
  }> {
    const startTime = Date.now();

    try {
      // One call to rule them all - no project filter means get all for user
      // Add cache busting to ensure fresh data
      const response = await branchApiV2.getBulkSummaries(undefined, false, true) as BulkSummaryResponse;

      if (!response.success) {
        throw new Error(response.message || 'Failed to load bulk summaries');
      }

      // Convert response objects to arrays for easier consumption
      const branches = Object.values(response.summaries || {});
      const projects = Object.values(response.projects || {});

      const queryTime = response.metadata?.queryTimeMs || (Date.now() - startTime);
      const fromCache = response.metadata?.fromCache || false;

      logger.info(`✅ Loaded ${branches.length} branches across ${projects.length} projects in ${queryTime}ms ${fromCache ? '(cached)' : '(fresh)'}`);

      return { branches, projects };
    } catch (error: unknown) {
      logger.error('❌ Failed to load user summaries:', error);
      throw new Error(`Failed to load branch summaries: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Load summaries for specific projects
   * SINGLE API CALL with project filter
   */
  async loadProjectSummaries(projectIds: string[]): Promise<BranchSummary[]> {
    if (!projectIds || projectIds.length === 0) {
      return [];
    }

    const startTime = Date.now();

    try {
      const response = await branchApiV2.getBulkSummaries(projectIds, false, true) as BulkSummaryResponse;

      if (!response.success) {
        throw new Error(response.message || 'Failed to load project summaries');
      }

      const branches = Object.values(response.summaries || {});
      const queryTime = response.metadata?.queryTimeMs || (Date.now() - startTime);

      logger.info(`✅ Loaded ${branches.length} branches for ${projectIds.length} projects in ${queryTime}ms`);

      return branches;
    } catch (error: unknown) {
      logger.error('❌ Failed to load project summaries:', error);
      throw new Error(`Failed to load project summaries: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Load summary for a single project
   * Uses bulk API for consistency and caching benefits
   */
  async loadSingleProjectSummary(projectId: string): Promise<BranchSummary[]> {
    return this.loadProjectSummaries([projectId]);
  }

  /**
   * Refresh summaries with cache bypass
   * Forces fresh data from database
   */
  async refreshSummaries(projectIds?: string[]): Promise<{
    branches: BranchSummary[];
    projects: ProjectSummary[];
  }> {
    logger.info('🔄 Refreshing summaries with cache bypass...');

    // Add a cache-busting timestamp parameter to force fresh data
    const response = await branchApiV2.getBulkSummaries(projectIds, false, true) as BulkSummaryResponse;

    if (!response.success) {
      throw new Error(response.message || 'Failed to refresh summaries');
    }

    const branches = Object.values(response.summaries || {});
    const projects = Object.values(response.projects || {});

    logger.info(`🔄 Refreshed ${branches.length} branches, ${projects.length} projects`);

    return { branches, projects };
  }

  /**
   * AGGRESSIVE cache bypass - clears ALL frontend caches
   * Use this for debugging cache issues
   */
  async forceRefreshSummaries(projectIds?: string[]): Promise<{
    branches: BranchSummary[];
    projects: ProjectSummary[];
  }> {
    logger.warn('🚨 FORCE REFRESH: Clearing ALL frontend caches...');

    // 1. Clear request deduplication cache entirely
    logger.warn('  1️⃣ Clearing request deduplication cache...');
    clearDeduplicationCache();

    // 2. Invalidate specific bulk summaries requests
    logger.warn('  2️⃣ Invalidating bulk summaries cache...');
    invalidateRequestCache('/api/v2/branches/summaries/bulk', 'POST');

    // 3. Log cache clearing for debugging
    logger.warn('  3️⃣ Using aggressive cache busting API call...');

    // 4. Use the force API call with aggressive cache busting
    const response = await branchApiV2.forceGetBulkSummaries(projectIds, false) as BulkSummaryResponse;

    if (!response.success) {
      logger.error('🚨 FORCE REFRESH FAILED:', response);
      throw new Error(response.message || 'Failed to force refresh summaries');
    }

    const branches = Object.values(response.summaries || {});
    const projects = Object.values(response.projects || {});

    // 5. Log task counts for debugging
    const totalTasks = branches.reduce((sum, branch) => sum + (branch.task_count || 0), 0);
    logger.warn(`🚨 FORCE REFRESH SUCCESS: ${branches.length} branches, ${projects.length} projects`);
    logger.warn(`📊 TOTAL TASK COUNT: ${totalTasks} tasks`);

    // 6. Log individual branch task counts for debugging
    branches.forEach(branch => {
      if (branch.task_count > 0) {
        logger.info(`📊 Branch "${branch.name}": ${branch.task_count} tasks`);
      }
    });

    return { branches, projects };
  }

  /**
   * Get performance metrics from last bulk call
   */
  getLastPerformanceMetrics() {
    // This could be enhanced to store metrics from last call
    // For now, return placeholder
    return {
      queryTimeMs: 0,
      fromCache: false,
      branchCount: 0,
      projectCount: 0
    };
  }
}

// Export singleton instance
export const branchService = new BranchService();
