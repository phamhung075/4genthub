import React from 'react';
import ReactDOM from 'react-dom/client';
import { vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import App from '../App';
import reportWebVitals from '../reportWebVitals';

// Mock dependencies
vi.mock('react-dom/client');
vi.mock('../App', () => ({
  __esModule: true,
  default: () => <div>Mocked App</div>,
}));
vi.mock('../reportWebVitals');
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div data-testid="browser-router">{children}</div>,
}));

// Mock CSS imports
vi.mock('../index.css', () => ({}));
vi.mock('../theme/global.scss', () => ({}));
vi.mock('../styles/notifications.css', () => ({}));

// Mock extension error filter
const mockInitializeExtensionErrorFilter = vi.fn();
vi.mock('../utils/extensionErrorFilter', () => ({
  initializeExtensionErrorFilter: mockInitializeExtensionErrorFilter,
}));

// Mock logger
vi.mock('../utils/logger', () => ({
  __esModule: true,
  default: {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock logger config
const mockDebugLoggerConfig = vi.fn();
vi.mock('../config/logger.config', () => ({
  debugLoggerConfig: mockDebugLoggerConfig,
}));

// Mock loggerExport
const mockLoggerExportModule = {
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
};

// Create a mock promise that we can control
let loggerExportResolve: (value: any) => void;
let loggerExportReject: (error: Error) => void;
const mockLoggerExportPromise = new Promise((resolve, reject) => {
  loggerExportResolve = resolve;
  loggerExportReject = reject;
});

vi.mock('../utils/loggerExport', () => ({
  __esModule: true,
  default: mockLoggerExportPromise,
}));

describe('index.tsx', () => {
  let mockRoot: any;
  let mockRender: ReturnType<typeof vi.fn>;
  let container: HTMLElement;
  let originalImport: typeof import;

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();

    // Store original import
    originalImport = (global as any).import;
    
    // Mock dynamic import
    (global as any).import = vi.fn((path: string) => {
      if (path === './utils/loggerExport') {
        return mockLoggerExportPromise;
      }
      return originalImport(path);
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
    (ReactDOM.createRoot as ReturnType<typeof vi.fn>).mockReturnValue(mockRoot);
  });

  afterEach(() => {
    // Clean up DOM
    if (document.body.contains(container)) {
      document.body.removeChild(container);
    }
    
    // Restore original import
    (global as any).import = originalImport;
    
    // Clear module cache to ensure fresh imports
    vi.resetModules();
  });

  it('initializes extension error filter before any other code', () => {
    // Import index to trigger execution
    require('../index');

    expect(mockInitializeExtensionErrorFilter).toHaveBeenCalledTimes(1);
    expect(mockInitializeExtensionErrorFilter).toHaveBeenCalledBefore(mockDebugLoggerConfig);
  });

  it('calls debugLoggerConfig after extension error filter', () => {
    require('../index');

    expect(mockDebugLoggerConfig).toHaveBeenCalledTimes(1);
    expect(mockDebugLoggerConfig).toHaveBeenCalledAfter(mockInitializeExtensionErrorFilter);
  });

  it('initializes logger export module asynchronously', async () => {
    require('../index');

    expect((global as any).import).toHaveBeenCalledWith('./utils/loggerExport');
    
    // Resolve the promise to test success case
    loggerExportResolve(mockLoggerExportModule);
    await mockLoggerExportPromise;

    // Verify the promise was handled
    expect((global as any).import).toHaveBeenCalledTimes(1);
  });

  it('handles logger export module initialization failure silently', async () => {
    require('../index');

    // Reject the promise to test error case
    const error = new Error('Logger initialization failed');
    loggerExportReject(error);
    
    try {
      await mockLoggerExportPromise;
    } catch (e) {
      // Expected to catch the error
    }

    // Should not throw and should continue execution
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('creates root with correct element', () => {
    require('../index');

    expect(ReactDOM.createRoot).toHaveBeenCalledWith(container);
  });

  it('renders App component wrapped in providers', () => {
    require('../index');

    expect(mockRender).toHaveBeenCalledTimes(1);
    
    // Get the rendered component
    const renderedComponent = mockRender.mock.calls[0][0];
    
    // Check structure
    expect(renderedComponent.type).toBe(React.StrictMode);
    expect(renderedComponent.props.children.type.name).toBe('BrowserRouter');
    expect(renderedComponent.props.children.props.children.type.name).toBe('default');
  });

  it('calls reportWebVitals', () => {
    require('../index');

    expect(reportWebVitals).toHaveBeenCalledTimes(1);
    expect(reportWebVitals).toHaveBeenCalledWith();
  });

  it('handles missing root element gracefully', () => {
    // Remove root element
    document.body.removeChild(container);

    // Mock getElementById to return null
    const originalGetElementById = document.getElementById;
    document.getElementById = vi.fn().mockReturnValue(null);

    // Should throw when trying to create root with null
    expect(() => {
      require('../index');
    }).toThrow();

    // Restore original function
    document.getElementById = originalGetElementById;
  });

  it('imports all required CSS files', () => {
    // This test verifies that CSS imports don't throw errors
    expect(() => {
      require('../index');
    }).not.toThrow();
  });

  it('wraps App in React.StrictMode', () => {
    require('../index');

    const renderedComponent = mockRender.mock.calls[0][0];
    expect(renderedComponent.type).toBe(React.StrictMode);
  });

  it('wraps App in BrowserRouter', () => {
    require('../index');

    const renderedComponent = mockRender.mock.calls[0][0];
    const browserRouter = renderedComponent.props.children;
    
    expect(browserRouter.type).toBeDefined();
    expect(browserRouter.props.children.type.name).toBe('default'); // App component
  });

  it('renders only once', () => {
    require('../index');

    expect(ReactDOM.createRoot).toHaveBeenCalledTimes(1);
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('maintains correct component hierarchy', () => {
    require('../index');

    const renderedComponent = mockRender.mock.calls[0][0];
    
    // Verify the complete hierarchy
    // StrictMode > BrowserRouter > App
    const strictMode = renderedComponent;
    const browserRouter = strictMode.props.children;
    const app = browserRouter.props.children;

    expect(strictMode.type).toBe(React.StrictMode);
    expect(browserRouter.type.name).toBe('BrowserRouter');
    expect(app.type.name).toBe('default'); // Default export from App
  });

  it('handles synchronous import errors gracefully', () => {
    // Test the try-catch block for synchronous errors
    const originalImport = (global as any).import;
    (global as any).import = vi.fn(() => {
      throw new Error('Synchronous import error');
    });

    // Should not throw when importing index
    expect(() => {
      require('../index');
    }).not.toThrow();

    // Should still render the app
    expect(mockRender).toHaveBeenCalledTimes(1);

    (global as any).import = originalImport;
  });

  it('executes initialization in correct order', () => {
    require('../index');

    // Verify order of operations
    const callOrder = [
      mockInitializeExtensionErrorFilter,
      mockDebugLoggerConfig,
      ReactDOM.createRoot,
      mockRender,
      reportWebVitals,
    ];

    // Check each function was called in order
    for (let i = 0; i < callOrder.length - 1; i++) {
      expect(callOrder[i]).toHaveBeenCalledBefore(callOrder[i + 1]);
    }
  });
});