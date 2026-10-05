/**
 * Notification bell and inbox.
 *
 * The dashboard push surface: an unread badge on the bell, and a panel listing what the store
 * holds, with mark-all-read (opening the panel) and per-item dismiss. useRealtimeSync feeds the
 * store from the realtime socket, so live frames and reconnect replays land here alike.
 */

import { useState } from 'react';
import { Bell, X } from 'lucide-react';
import { useNotificationStore } from '../store/notifications';

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const notifications = useNotificationStore((state) => state.notifications);
  const unreadCount = useNotificationStore((state) => state.unreadCount);
  const ackAll = useNotificationStore((state) => state.ackAll);
  const dismiss = useNotificationStore((state) => state.dismiss);
  const reset = useNotificationStore((state) => state.reset);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && unreadCount > 0) {
      // Opening the inbox is the read action; the count clears, the items stay.
      ackAll();
    }
  };

  return (
    <div className="relative">
      <button
        onClick={toggle}
        aria-label={`Notifications (${unreadCount} unread)`}
        title="Notifications"
        className="relative flex items-center justify-center w-10 h-10 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span
            data-testid="notification-unread-count"
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] leading-[18px] text-center"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          data-testid="notification-inbox"
          className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto rounded-lg border border-surface-border bg-surface shadow-xl z-[1100]"
        >
          <div className="flex items-center justify-between px-3 py-2 border-b border-surface-border">
            <span className="font-medium text-sm">Notifications</span>
            <button onClick={reset} className="text-xs underline" disabled={notifications.length === 0}>
              Clear all
            </button>
          </div>

          {notifications.length === 0 ? (
            <p className="px-3 py-4 text-sm text-muted-foreground">
              Nothing yet. Messages sent to you from a seat arrive here.
            </p>
          ) : (
            <ul>
              {notifications.map((notification) => (
                <li
                  key={notification.id}
                  className="flex items-start gap-2 px-3 py-2 border-b border-surface-border last:border-b-0"
                >
                  <div className="flex-1 text-sm">
                    <span className="font-medium">{notification.from ? `${notification.from}: ` : ''}</span>
                    <span>{notification.message}</span>
                    <div className="text-xs text-muted-foreground">
                      {new Date(notification.receivedAt).toLocaleTimeString()}
                      {notification.kind ? ` · ${notification.kind}` : ''}
                    </div>
                  </div>
                  <button
                    onClick={() => dismiss(notification.id)}
                    aria-label={`Dismiss notification ${notification.id}`}
                    className="p-1 rounded hover:bg-primary/10"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
