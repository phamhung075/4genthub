import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

describe('Toast Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
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
    jest.useFakeTimers();
    
    render(<WrappedTestComponent />);
    
    fireEvent.click(screen.getByTestId('show-success'));
    
    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
    });

    // Fast-forward time by 5 seconds (default duration)
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(screen.queryByText('Success!')).not.toBeInTheDocument();
    });
    
    jest.useRealTimers();
  });

  it('applies correct styles for different toast types', async () => {
    render(<WrappedTestComponent />);
    
    fireEvent.click(screen.getByTestId('show-success'));
    fireEvent.click(screen.getByTestId('show-error'));
    
    await waitFor(() => {
      const successToast = screen.getByText('Success!').closest('[role="alert"]');
      const errorToast = screen.getByText('Error!').closest('[role="alert"]');
      
      expect(successToast).toHaveClass('border-green-500');
      expect(errorToast).toHaveClass('border-red-500');
    });
  });
});