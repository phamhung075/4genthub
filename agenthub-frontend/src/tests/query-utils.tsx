import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Creates a test QueryClient with retries disabled and garbage collection off.
 * A fresh client is created per call, so tests are already isolated; Infinity
 * (React Query v5's only way to disable collection) keeps an unobserved entry
 * alive for the duration of a test so a delayed write cannot race collection.
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed requests in tests
        // gcTime: 0 would collect an unobserved entry immediately in React Query v5. A fresh
        // client per call already isolates tests, so Infinity (which actually disables
        // collection) is the value that matches the intent of this helper.
        gcTime: Infinity,
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
