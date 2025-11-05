/**
 * Test Utilities - Comprehensive Test Providers
 *
 * Provides all necessary context providers for testing after Redux→Zustand migration:
 * - BrowserRouter (routing)
 * - AuthProvider (authentication)
 * - QueryClientProvider (React Query)
 *
 * Usage:
 *   import { render } from './test-utils';
 *   render(<MyComponent />);
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import type { RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../contexts/AuthContext';

/**
 * Create a fresh QueryClient for each test to avoid cache pollution
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
        gcTime: 0, // Disable garbage collection
        staleTime: 0, // Data always stale in tests
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * All-the-providers wrapper for tests
 * Wraps components in necessary context providers:
 * - BrowserRouter: Required for components using useNavigate, useLocation, etc.
 * - QueryClientProvider: Required for React Query hooks
 * - AuthProvider: Required for useAuth hook
 */
function AllTheProviders({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
}

/**
 * Custom render function with Router context
 *
 * Wraps all rendered components in BrowserRouter to support React Router hooks.
 * This prevents "useNavigate() may be used only in the context of a <Router>" errors.
 *
 * @param ui - React component to render
 * @param options - Standard RTL render options
 * @returns Render result
 */
export function customRender(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
): RenderResult {
  return render(ui, { wrapper: AllTheProviders, ...options });
}

// Re-export everything from React Testing Library
export * from '@testing-library/react';

// Override render with our custom version (for future extensibility)
export { customRender as render };
