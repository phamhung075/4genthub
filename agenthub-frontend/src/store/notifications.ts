/**
 * Dashboard notification inbox.
 *
 * Frames arrive on the realtime socket (payload.entity 'notification', posted by the client or
 * replayed by the server on reconnect). They are kept here so an agent-to-human message stays
 * legible after its toast has gone. This store holds no server state of its own: dedupe is by
 * frame id, so a replay of the same notification cannot double-count.
 */

import { create } from 'zustand';

export interface DashboardNotification {
  /** The frame's entity id (metadata.entity_id, or the frame id when absent). */
  id: string;
  message: string;
  from?: string;
  room?: string;
  seat?: string;
  kind?: string;
  receivedAt: string;
  read: boolean;
}

export type NewDashboardNotification = Omit<DashboardNotification, 'receivedAt' | 'read'>;

interface NotificationState {
  notifications: DashboardNotification[];
  unreadCount: number;
  add: (notification: NewDashboardNotification) => void;
  ack: (id: string) => void;
  ackAll: () => void;
  dismiss: (id: string) => void;
  /** Clear the inbox: the UI's Clear all, and the seam tests use to reset the module-global store. */
  reset: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  add: (notification) =>
    set((state) => {
      if (state.notifications.some((n) => n.id === notification.id)) {
        return state;
      }
      const entry: DashboardNotification = {
        ...notification,
        receivedAt: new Date().toISOString(),
        read: false,
      };
      return { notifications: [entry, ...state.notifications], unreadCount: state.unreadCount + 1 };
    }),

  ack: (id) =>
    set((state) => {
      const target = state.notifications.find((n) => n.id === id);
      if (!target || target.read) {
        return state;
      }
      return {
        notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
        unreadCount: Math.max(0, state.unreadCount - 1),
      };
    }),

  ackAll: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => (n.read ? n : { ...n, read: true })),
      unreadCount: 0,
    })),

  dismiss: (id) =>
    set((state) => {
      const target = state.notifications.find((n) => n.id === id);
      return {
        notifications: state.notifications.filter((n) => n.id !== id),
        unreadCount: target && !target.read ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
      };
    }),

  reset: () => set({ notifications: [], unreadCount: 0 }),
}));
