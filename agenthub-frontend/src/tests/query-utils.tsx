import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Creates a test QueryClient with disabled retries and cache
 * to ensure tests run fast and predictably
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed requests in tests
        gcTime: 0, // Don't cache between tests
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
