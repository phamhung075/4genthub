import React from 'react';
import { render, screen, fireEvent, waitFor, act } from './../../test-utils';
import { ToastProvider, useToast, useSuccessToast, useErrorToast } from '../../../components/ui/toast';

// Test component that uses toast hooks
const TestToastComponent: React.FC = () => {
  const { showToast, dismissAll } = useToast();
  const showSuccess = useSuccessToast();
  const showError = useErrorToast();

  return (
    <div>
      <button
        onClick={() => showSuccess('Success!', 'Everything worked perfectly')}
        data-testid="show-success"
      >
        Show Success
      </button>
      <button
        onClick={() => showError('Error!', 'Something went wrong')}
        data-testid="show-error"
      >
        Show Error
      </button>
      <button
        onClick={() => showToast({
          type: 'info',
          title: 'Info Message',
          description: 'This is information',
          action: {
            label: 'Action',
            onClick: () => console.log('Action clicked')
          }
        })}
        data-testid="show-info"
      >
        Show Info with Action
      </button>
      <button onClick={dismissAll} data-testid="dismiss-all">
        Dismiss All
      </button>
    </div>
  );
};

const WrappedTestComponent: React.FC = () => (
  <ToastProvider>
    <TestToastComponent />
  </ToastProvider>
);

/**
 * The two pins for the toast hooks' rules-of-hooks violation (task e6ca3f6c).
 *
 * PIN ONE is the identity: the same function reference across re-renders, both inside a
 * provider and - the case that matters - OUTSIDE one. Predicted to fail on the old code
 * because it returned a fresh `() => ''` per call outside a provider; inside a provider
 * it already returned a useCallback'd function, so only the outside half discriminates.
 *
 * PIN TWO is the hook order: a component whose provider is TOGGLED between renders. The
 * old shape called useContext + useCallback inside a provider and useContext + an early
 * return outside, so the hook COUNT changed with a context value - React throws in dev,
 * and in a production build it is not absent, it is UNDEFINED.
 */
describe('toast hooks - identity and hook order', () => {
  it('returns the SAME function across re-renders, inside and outside a provider', () => {
    const seen: Array<() => unknown> = [];
    const Probe: React.FC<{ tick: number }> = ({ tick }) => {
      seen.push(useSuccessToast());
      return <span>{tick}</span>;
    };

    const bare = render(<Probe tick={0} />);
    bare.rerender(<Probe tick={1} />);
    expect(seen).toHaveLength(2);
    expect(seen[0]).toBe(seen[1]);

    // The inside-provider half, for completeness: it passed on the old code too.
    seen.length = 0;
    const wrapped = render(
      <ToastProvider>
        <Probe tick={0} />
      </ToastProvider>
    );
    wrapped.rerender(
      <ToastProvider>
        <Probe tick={1} />
      </ToastProvider>
    );
    expect(seen).toHaveLength(2);
    expect(seen[0]).toBe(seen[1]);
  });

  it('calls the same number of hooks whether or not a provider is present', () => {
    const Probe: React.FC<{ tick: number }> = ({ tick }) => {
      useSuccessToast();
      return <span>{tick}</span>;
    };
    const Toggling: React.FC<{ wrap: boolean }> = ({ wrap }) => {
      const inner = <Probe tick={wrap ? 1 : 0} />;
      return wrap ? <ToastProvider>{inner}</ToastProvider> : inner;
    };

    const view = render(<Toggling wrap />);
    expect(() => view.rerender(<Toggling wrap={false} />)).not.toThrow();
  });
});

describe('Toast Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders success toast correctly', async () => {
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-success'));

    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
      expect(screen.getByText('Everything worked perfectly')).toBeInTheDocument();
    });
  });

  it('renders error toast correctly', async () => {
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-error'));

    await waitFor(() => {
      expect(screen.getByText('Error!')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });
  });

  it('renders toast with action button', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-info'));

    await waitFor(() => {
      expect(screen.getByText('Info Message')).toBeInTheDocument();
      expect(screen.getByText('This is information')).toBeInTheDocument();
      expect(screen.getByText('Action')).toBeInTheDocument();
    });

    // Click the action button
    fireEvent.click(screen.getByText('Action'));
    expect(consoleSpy).toHaveBeenCalledWith('Action clicked');

    consoleSpy.mockRestore();
  });

  it('allows dismissing individual toasts', async () => {
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-success'));

    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
    });

    // Find and click the close button
    const closeButton = screen.getByLabelText('Close notification');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('Success!')).not.toBeInTheDocument();
    });
  });

  it('dismisses all toasts when dismissAll is called', async () => {
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-success'));
    fireEvent.click(screen.getByTestId('show-error'));

    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
      expect(screen.getByText('Error!')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('dismiss-all'));

    await waitFor(() => {
      expect(screen.queryByText('Success!')).not.toBeInTheDocument();
      expect(screen.queryByText('Error!')).not.toBeInTheDocument();
    });
  });

  it('auto-dismisses toasts after specified duration', async () => {
    vi.useFakeTimers();
    try {
      render(<WrappedTestComponent />);

      fireEvent.click(screen.getByTestId('show-success'));
      expect(screen.getByText('Success!')).toBeInTheDocument();

      // Fast-forward time by 5 seconds (default duration)
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(screen.queryByText('Success!')).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('applies correct styles for different toast types', async () => {
    render(<WrappedTestComponent />);

    fireEvent.click(screen.getByTestId('show-success'));
    fireEvent.click(screen.getByTestId('show-error'));

    await waitFor(() => {
      const successToast = screen.getByText('Success!').closest('[role="alert"]');
      const errorToast = screen.getByText('Error!').closest('[role="alert"]');

      expect(successToast).toHaveClass('border-success');
      expect(errorToast).toHaveClass('border-error');
    });
  });
});
