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
      const response = await branchApiV2.getBulkSummaries() as BulkSummaryResponse;

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
    } catch (error: any) {
      logger.error('❌ Failed to load user summaries:', error);
      throw new Error(`Failed to load branch summaries: ${error.message}`);
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
      const response = await branchApiV2.getBulkSummaries(projectIds) as BulkSummaryResponse;

      if (!response.success) {
        throw new Error(response.message || 'Failed to load project summaries');
      }

      const branches = Object.values(response.summaries || {});
      const queryTime = response.metadata?.queryTimeMs || (Date.now() - startTime);

      logger.info(`✅ Loaded ${branches.length} branches for ${projectIds.length} projects in ${queryTime}ms`);

      return branches;
    } catch (error: any) {
      logger.error('❌ Failed to load project summaries:', error);
      throw new Error(`Failed to load project summaries: ${error.message}`);
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
    const response = await branchApiV2.getBulkSummaries(projectIds) as BulkSummaryResponse;

    if (!response.success) {
      throw new Error(response.message || 'Failed to refresh summaries');
    }

    const branches = Object.values(response.summaries || {});
    const projects = Object.values(response.projects || {});

    logger.info(`🔄 Refreshed ${branches.length} branches, ${projects.length} projects`);

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