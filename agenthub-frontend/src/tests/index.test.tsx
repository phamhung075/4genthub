import React from 'react';
import ReactDOM from 'react-dom/client';
import { vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import App from '../App';
import reportWebVitals from '../reportWebVitals';

// Shared state created with vi.hoisted so the hoisted vi.mock factories below
// never reference a variable that has not been initialized yet.
const mocks = vi.hoisted(() => ({
  initializeExtensionErrorFilter: vi.fn(),
  debugLoggerConfig: vi.fn(),
}));

const loggerState = vi.hoisted(() => ({
  imported: false,
  promise: Promise.resolve({}) as Promise<unknown>,
  reject: (_error: Error) => {},
}));

// Mock dependencies
vi.mock('react-dom/client', () => ({
  __esModule: true,
  default: { createRoot: vi.fn() },
}));
vi.mock('../App', () => ({
  __esModule: true,
  default: () => <div>Mocked App</div>,
}));
vi.mock('../reportWebVitals');
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="browser-router">{children}</div>
  ),
}));

// Mock CSS imports
vi.mock('../index.css', () => ({}));
vi.mock('../theme/global.css', () => ({}));
vi.mock('../styles/notifications.css', () => ({}));

// Mock extension error filter
vi.mock('../utils/extensionErrorFilter', () => ({
  initializeExtensionErrorFilter: mocks.initializeExtensionErrorFilter,
}));

// Mock logger config
vi.mock('../config/logger.config', () => ({
  debugLoggerConfig: mocks.debugLoggerConfig,
}));

describe('index.tsx', () => {
  let mockRoot: any;
  let mockRender: ReturnType<typeof vi.fn>;
  let container: HTMLElement;
  let originalGetElementById: typeof document.getElementById;

  const loadIndex = () => import('../index');

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();

    // Fresh logger-export mock for every test. vi.doMock is not hoisted and is
    // picked up by the dynamic import('../index') below.
    loggerState.imported = false;
    loggerState.promise = new Promise<unknown>((_resolve, reject) => {
      loggerState.reject = reject;
    });
    vi.doMock('../utils/loggerExport', () => {
      loggerState.imported = true;
      return { __esModule: true, default: loggerState.promise };
    });

    // Create a mock container
    container = document.createElement('div');
    container.id = 'root';
    document.body.appendChild(container);

    // Mock ReactDOM.createRoot
    mockRender = vi.fn();
    mockRoot = {
      render: mockRender,
    };
    (ReactDOM.createRoot as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockRoot);
  });

  afterEach(() => {
    // Clean up DOM
    if (document.body.contains(container)) {
      document.body.removeChild(container);
    }

    // Clear module cache to ensure fresh imports
    vi.resetModules();
  });

  it('initializes extension error filter before any other code', async () => {
    await loadIndex();

    expect(mocks.initializeExtensionErrorFilter).toHaveBeenCalledTimes(1);
    expect(mocks.initializeExtensionErrorFilter).toHaveBeenCalledBefore(mocks.debugLoggerConfig);
  });

  it('calls debugLoggerConfig after extension error filter', async () => {
    await loadIndex();

    expect(mocks.debugLoggerConfig).toHaveBeenCalledTimes(1);
    expect(mocks.debugLoggerConfig).toHaveBeenCalledAfter(mocks.initializeExtensionErrorFilter);
  });

  it('initializes logger export module asynchronously', async () => {
    await loadIndex();

    // A FIXED NUMBER OF MICROTASKS WAS NEVER THE CONTRACT: the logger module resolves when the
    // runner's module graph says so, and Vitest 4 hands it over a turn later than 3.x did - so this
    // waited on a tick rather than on the CONDITION the case is actually about.
    await vi.waitFor(() => expect(loggerState.imported).toBe(true));
  });

  it('renders the app when the logger export default is a rejected promise', async () => {
    const error = new Error('Logger initialization failed');
    loggerState.reject(error);
    await loggerState.promise.catch(() => {});

    await expect(loadIndex()).resolves.toBeDefined();
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('creates root with correct element', async () => {
    await loadIndex();

    expect(ReactDOM.createRoot).toHaveBeenCalledWith(container);
  });

  it('renders App component wrapped in providers', async () => {
    await loadIndex();

    expect(mockRender).toHaveBeenCalledTimes(1);

    // Get the rendered component
    const renderedComponent = mockRender.mock.calls[0][0];

    // Check structure: StrictMode > QueryClientProvider > BrowserRouter > App
    expect(renderedComponent.type).toBe(React.StrictMode);
    const provider = renderedComponent.props.children;
    expect(provider.type).toBe(QueryClientProvider);
    const browserRouter = provider.props.children[0];
    expect(browserRouter.type).toBe(BrowserRouter);
    expect(browserRouter.props.children.type).toBe(App);
  });

  it('calls reportWebVitals', async () => {
    await loadIndex();

    expect(reportWebVitals).toHaveBeenCalledTimes(1);
    expect(reportWebVitals).toHaveBeenCalledWith();
  });

  it('throws when the root element is missing', async () => {
    // Remove root element
    document.body.removeChild(container);

    // Mock getElementById to return null
    originalGetElementById = document.getElementById;
    document.getElementById = vi.fn().mockReturnValue(null);

    // Real react-dom raises when handed a null container; emulate it here so the
    // entry's forwarding of the missing element is observable.
    (ReactDOM.createRoot as unknown as ReturnType<typeof vi.fn>).mockImplementation((element: any) => {
      if (!element) {
        throw new Error('Target container is not a DOM element');
      }
      return mockRoot;
    });

    await expect(loadIndex()).rejects.toThrow('Target container is not a DOM element');

    // Restore original function
    document.getElementById = originalGetElementById;
  });

  it('imports all required CSS files', async () => {
    // This test verifies that CSS imports don't throw errors
    await expect(loadIndex()).resolves.toBeDefined();
  });

  it('wraps App in React.StrictMode', async () => {
    await loadIndex();

    const renderedComponent = mockRender.mock.calls[0][0];
    expect(renderedComponent.type).toBe(React.StrictMode);
  });

  it('wraps App in BrowserRouter', async () => {
    await loadIndex();

    const renderedComponent = mockRender.mock.calls[0][0];
    const browserRouter = renderedComponent.props.children.props.children[0];

    expect(browserRouter.type).toBe(BrowserRouter);
    expect(browserRouter.props.children.type).toBe(App); // App component
  });

  it('renders only once', async () => {
    await loadIndex();

    expect(ReactDOM.createRoot).toHaveBeenCalledTimes(1);
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('maintains correct component hierarchy', async () => {
    await loadIndex();

    const renderedComponent = mockRender.mock.calls[0][0];

    // Verify the complete hierarchy
    // StrictMode > QueryClientProvider > BrowserRouter > App
    const provider = renderedComponent.props.children;
    const browserRouter = provider.props.children[0];
    const app = browserRouter.props.children;

    expect(renderedComponent.type).toBe(React.StrictMode);
    expect(provider.type).toBe(QueryClientProvider);
    expect(browserRouter.type).toBe(BrowserRouter);
    expect(app.type).toBe(App); // Default export from App
  });

  it('handles synchronous import errors gracefully', async () => {
    // Make the logger export module itself fail to load.
    vi.doMock('../utils/loggerExport', () => {
      throw new Error('Synchronous import error');
    });

    // Should not throw when importing index
    await expect(loadIndex()).resolves.toBeDefined();

    // Should still render the app
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('executes initialization in correct order', async () => {
    await loadIndex();

    // Verify order of operations
    const callOrder = [
      mocks.initializeExtensionErrorFilter,
      mocks.debugLoggerConfig,
      ReactDOM.createRoot as unknown as ReturnType<typeof vi.fn>,
      mockRender,
      reportWebVitals as unknown as ReturnType<typeof vi.fn>,
    ];

    // Check each function was called in order
    for (let i = 0; i < callOrder.length - 1; i++) {
      expect(callOrder[i]).toHaveBeenCalledBefore(callOrder[i + 1]);
    }
  });
});
