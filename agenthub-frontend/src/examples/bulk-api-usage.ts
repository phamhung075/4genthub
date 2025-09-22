/**
 * Example Usage of Bulk API Implementation
 *
 * This file demonstrates how to use the new bulk API endpoint
 * for efficient branch summary loading.
 */

import { useBranchSummaries, useAllBranchSummaries, useProjectSummaries } from '../hooks/useBranchSummaries';
import { branchService } from '../services/branchService';
import { getBulkBranchSummaries } from '../api';

// Example 1: Using React Hook for All User Summaries
function ExampleComponent1() {
  const {
    summaries,
    projects,
    loading,
    error,
    refresh
  } = useBranchSummaries();

  if (loading) return <div>Loading all branch summaries...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>All Projects ({projects.length})</h2>
      <h3>All Branches ({summaries.length})</h3>
      <button onClick={refresh}>Refresh Data</button>

      {summaries.map(branch => (
        <div key={branch.id}>
          {branch.name}: {branch.total_tasks} tasks
        </div>
      ))}
    </div>
  );
}

// Example 2: Using React Hook for Specific Projects
function ExampleComponent2() {
  const projectIds = ['project-1', 'project-2'];
  const { summaries, loading, error } = useProjectSummaries(projectIds[0]);

  return (
    <div>
      <h2>Specific Project Branches</h2>
      {loading && <div>Loading project summaries...</div>}
      {error && <div>Error: {error}</div>}
      {summaries.map(branch => (
        <div key={branch.id}>
          {branch.name}: {branch.total_tasks} tasks ({branch.progress_percentage}% complete)
        </div>
      ))}
    </div>
  );
}

// Example 3: Using Auto-Refresh Hook
function ExampleComponent3() {
  const {
    summaries,
    projects,
    loading,
    refreshing
  } = useAllBranchSummaries(30000); // Refresh every 30 seconds

  return (
    <div>
      <h2>Auto-Refreshing Dashboard</h2>
      {loading && <div>Initial loading...</div>}
      {refreshing && <div>Refreshing data...</div>}

      <div>Projects: {projects.length}</div>
      <div>Total Branches: {summaries.length}</div>
      <div>Total Tasks: {summaries.reduce((sum, b) => sum + b.total_tasks, 0)}</div>
    </div>
  );
}

// Example 4: Using Service Directly (for programmatic use)
async function loadDataProgrammatically() {
  try {
    // Load all user summaries
    const { branches, projects } = await branchService.loadUserSummaries();
    console.log(`Loaded ${branches.length} branches across ${projects.length} projects`);

    // Load specific project summaries
    const projectBranches = await branchService.loadProjectSummaries(['project-1', 'project-2']);
    console.log(`Loaded ${projectBranches.length} branches for specific projects`);

    // Refresh with cache bypass
    const refreshedData = await branchService.refreshSummaries();
    console.log(`Refreshed data: ${refreshedData.branches.length} branches`);

  } catch (error) {
    console.error('Failed to load branch summaries:', error);
  }
}

// Example 5: Using Low-Level API Directly
async function lowLevelApiUsage() {
  try {
    // Get all summaries for user
    const allSummaries = await getBulkBranchSummaries();
    console.log('Bulk response:', allSummaries);

    // Get summaries for specific projects
    const projectSummaries = await getBulkBranchSummaries(['project-1', 'project-2']);
    console.log('Project-specific summaries:', projectSummaries);

  } catch (error) {
    console.error('API call failed:', error);
  }
}

// Example 6: Performance Comparison
async function performanceComparison() {
  const startTime = Date.now();

  try {
    // NEW WAY: Single bulk API call
    const { branches, projects } = await branchService.loadUserSummaries();
    const newWayTime = Date.now() - startTime;

    console.log(`✅ NEW WAY: Loaded ${branches.length} branches in ${newWayTime}ms`);
    console.log(`📊 Performance: Single API call replaced ${projects.length} individual calls`);
    console.log(`🚀 Estimated improvement: ${projects.length * 100 - newWayTime}ms saved`);

  } catch (error) {
    console.error('Performance test failed:', error);
  }
}

export {
  ExampleComponent1,
  ExampleComponent2,
  ExampleComponent3,
  loadDataProgrammatically,
  lowLevelApiUsage,
  performanceComparison
};