import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Creates a test QueryClient with retries disabled. gcTime stays 0 so an unobserved
 * entry is collected immediately; that is deliberate here (see the comment inside
 * createTestQueryClient) and a fresh client per call already isolates tests.
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed requests in tests
        // Kept at 0 deliberately, and NOT because it "disables" collection: in React Query v5
        // gcTime 0 collects an unobserved entry immediately, and that collection is
        // load-bearing for useTaskData.test.tsx "should load full task on demand". The
        // task-list queryFn seeds ['task', id] with a summary, and loadFullTask's fetchQuery
        // would otherwise return that seed (within staleTime) instead of fetching the full
        // task. Switching this to Infinity breaks that test; fixing the seeding/fetchQuery
        // interaction is a product decision, reported separately. Each call already creates a
        // fresh QueryClient, so tests are isolated regardless of gcTime.
        gcTime: 0,
      },
      mutations: {
        retry: false, // Don't retry failed mutations in tests
      },
    },
  });
}

/**
 * Wrapper for rendering components with React Query context
 * Usage: renderWithQuery(<MyComponent />)
 */
export function renderWithQuery(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
    options
  );
}
