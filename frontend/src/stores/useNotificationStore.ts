import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { NotificationPayload, NotificationMessage } from '@/types';

export function useNotificationStore() {
  return defineStore('notifications', () => {
    // State
    const notifications = ref<NotificationPayload[]>([]);
    const wsMessages = ref<NotificationMessage[]>([]);
    const unreadCount = ref(0);
    const loading = ref(false);
    const error = ref<string | null>(null);

    function asArray<T>(value: unknown): T[] {
      return Array.isArray(value) ? (value as T[]) : [];
    }

    // Actions
    async function loadNotifications(limit: number = 30): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const list = await apiGet<NotificationPayload[]>(`/api/query/notifications/secure?limit=${limit}`);
        notifications.value = asArray<NotificationPayload>(list);
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load notifications';
      } finally {
        loading.value = false;
      }
    }

    function addNotification(notification: NotificationPayload): void {
      if (!Array.isArray(notifications.value)) {
        notifications.value = [];
      }
      notifications.value.unshift(notification);
      unreadCount.value++;
      // Keep only last 100
      if (notifications.value.length > 100) {
        notifications.value = notifications.value.slice(0, 100);
      }
    }

    function addWsMessage(message: NotificationMessage): void {
      if (!Array.isArray(wsMessages.value)) {
        wsMessages.value = [];
      }
      wsMessages.value.unshift(message);
      unreadCount.value++;
      // Keep only last 100
      if (wsMessages.value.length > 100) {
        wsMessages.value = wsMessages.value.slice(0, 100);
      }
    }

    function markAsRead(): void {
      unreadCount.value = 0;
    }

    let pollingTimer: ReturnType<typeof setInterval> | null = null;

    function startPolling(intervalMs: number = 3000): void {
      if (pollingTimer) return;
      loadNotifications();
      pollingTimer = setInterval(() => {
        loadNotifications();
      }, intervalMs);
    }

    function stopPolling(): void {
      if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
      }
    }

    function clear(): void {
      notifications.value = [];
      wsMessages.value = [];
      unreadCount.value = 0;
      error.value = null;
    }

    return {
      notifications,
      wsMessages,
      unreadCount,
      loading,
      error,
      loadNotifications,
      addNotification,
      addWsMessage,
      markAsRead,
      startPolling,
      stopPolling,
      clear,
    };
  })();
}
