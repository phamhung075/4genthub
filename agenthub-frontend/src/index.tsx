import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import './index.css';
import reportWebVitals from './reportWebVitals';
import './theme/global.scss';
import './styles/notifications.css';

// Configure React Query with optimal defaults
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes - data stays fresh
      gcTime: 10 * 60 * 1000, // 10 minutes - cache time (formerly cacheTime)
      retry: 1, // Only retry failed requests once
      refetchOnWindowFocus: false, // Don't refetch on window focus by default
    },
  },
});

// Initialize extension error filter at the earliest possible point
// This must happen before any other code to catch all extension errors
import { initializeExtensionErrorFilter } from './utils/extensionErrorFilter';
import logger from './utils/logger';
import { debugLoggerConfig } from './config/logger.config';
initializeExtensionErrorFilter();

// Debug: Log current logger configuration to verify environment variables loaded
debugLoggerConfig();

// Initialize logging system safely - only for errors
try {
  import('./utils/loggerExport').then(({ logger }) => {
    // Logger initialized successfully - no need to log startup
  }).catch(error => {
    // Silent fallback - logging system unavailable
  });
} catch (error) {
  // Silent fallback - basic mode
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} position="bottom-left" />
    </QueryClientProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

// HMR Client-Side Debugging (Development Only)
if (import.meta.hot) {
  console.log('🔥 HMR Client Initialized');

  // Log when updates are applied
  import.meta.hot.on('vite:beforeUpdate', (payload) => {
    console.log('⚡ HMR Update Received:', {
      type: payload.type,
      updates: payload.updates?.length || 0,
      timestamp: new Date().toISOString()
    });
  });

  // Log after updates are applied
  import.meta.hot.on('vite:afterUpdate', (payload) => {
    console.log('✅ HMR Update Applied:', {
      type: payload.type,
      timestamp: new Date().toISOString()
    });
  });

  // Log errors
  import.meta.hot.on('vite:error', (payload) => {
    console.error('❌ HMR Error:', {
      error: payload.err,
      timestamp: new Date().toISOString()
    });
  });

  // Log when full reload is needed
  import.meta.hot.on('vite:beforeFullReload', () => {
    console.warn('🔄 Full Page Reload Required');
  });

  // Log WebSocket connection status
  import.meta.hot.on('vite:ws:connect', () => {
    console.log('🔌 HMR WebSocket Connected');
  });

  import.meta.hot.on('vite:ws:disconnect', () => {
    console.warn('🔌 HMR WebSocket Disconnected');
  });
}
