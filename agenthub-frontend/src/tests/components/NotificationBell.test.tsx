/**
 * Tests for the notification bell and inbox: the dashboard push surface.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationBell } from '../../components/NotificationBell';
import { useNotificationStore } from '../../store/notifications';

describe('NotificationBell', () => {
  beforeEach(() => {
    useNotificationStore.getState().reset();
  });

  it('shows the unread count, lists the message and acks on open', () => {
    useNotificationStore.getState().add({ id: 'n1', message: 'ping from alice', from: 'alice', kind: 'agent_message' });

    render(<NotificationBell />);

    expect(screen.getByTestId('notification-unread-count')).toHaveTextContent('1');

    fireEvent.click(screen.getByRole('button', { name: /notifications/i }));

    expect(screen.getByTestId('notification-inbox')).toBeInTheDocument();
    expect(screen.getByText('ping from alice')).toBeInTheDocument();
    expect(screen.getByText(/alice:/)).toBeInTheDocument();
    // Opening the inbox is the read action.
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });

  it('dismisses a notification from the inbox', () => {
    useNotificationStore.getState().add({ id: 'n2', message: 'goodbye' });

    render(<NotificationBell />);
    fireEvent.click(screen.getByRole('button', { name: /notifications/i }));
    fireEvent.click(screen.getByRole('button', { name: /dismiss notification n2/i }));

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
    expect(screen.queryByText('goodbye')).not.toBeInTheDocument();
  });
});
