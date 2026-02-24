import { ref, onBeforeUnmount, readonly, type Ref, type DeepReadonly } from "vue";

export interface NotificationMessage {
  id: string;
  event_type: string;
  service: string;
  payload: Record<string, unknown>;
  correlation_id?: string;
  created_at: string;
}

export interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
}

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:18080/ws";
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

export function useWebSocket(
  token?: Ref<string | undefined>,
  onMessage?: (message: NotificationMessage) => void,
) {
  const ws = ref<WebSocket | null>(null);
  const state = ref<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0,
  });
  const messages = ref<NotificationMessage[]>([]);
  const reconnectTimer = ref<ReturnType<typeof setTimeout> | null>(null);

  const connect = () => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return;
    }

    if (state.value.connecting) {
      return;
    }

    state.value.connecting = true;
    state.value.error = null;

    try {
      const url = token?.value ? `${WS_URL}?token=${token.value}` : WS_URL;
      const socket = new WebSocket(url);

      socket.onopen = () => {
        state.value.connected = true;
        state.value.connecting = false;
        state.value.error = null;
        state.value.reconnectAttempts = 0;
        console.log("[WebSocket] Connected");

        // Subscribe to notification channels
        socket.send(
          JSON.stringify({
            action: "subscribe",
            channels: ["notifications", "events", "proposals"],
          }),
        );
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as NotificationMessage;
          messages.value.unshift(data);

          // Keep only last 100 messages
          if (messages.value.length > 100) {
            messages.value = messages.value.slice(0, 100);
          }

          onMessage?.(data);
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err);
        }
      };

      socket.onerror = (error) => {
        state.value.error = "WebSocket error occurred";
        state.value.connecting = false;
        console.error("[WebSocket] Error:", error);
      };

      socket.onclose = (event) => {
        state.value.connected = false;
        state.value.connecting = false;
        ws.value = null;

        if (!event.wasClean && state.value.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          state.value.reconnectAttempts++;
          const delay = RECONNECT_DELAY * Math.pow(2, state.value.reconnectAttempts - 1);
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${state.value.reconnectAttempts})`);
          
          reconnectTimer.value = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.value = socket;
    } catch (err) {
      state.value.error = err instanceof Error ? err.message : "Failed to connect";
      state.value.connecting = false;
    }
  };

  const disconnect = () => {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value);
      reconnectTimer.value = null;
    }

    if (ws.value) {
      ws.value.close(1000, "Client disconnecting");
      ws.value = null;
    }

    state.value.connected = false;
    state.value.connecting = false;
    state.value.reconnectAttempts = 0;
  };

  const send = (data: Record<string, unknown>) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data));
      return true;
    }
    return false;
  };

  const clearMessages = () => {
    messages.value = [];
  };

  // Auto-cleanup on component unmount
  onBeforeUnmount(() => {
    disconnect();
  });

  return {
    state: readonly(state) as DeepReadonly<Ref<WebSocketState>>,
    messages: readonly(messages) as DeepReadonly<Ref<NotificationMessage[]>>,
    connect,
    disconnect,
    send,
    clearMessages,
  };
}

// Composable for notification management with WebSocket
export function useRealtimeNotifications(token?: Ref<string | undefined>) {
  const unreadCount = ref(0);
  const latestNotification = ref<NotificationMessage | null>(null);

  const handleNewMessage = (message: NotificationMessage) => {
    unreadCount.value++;
    latestNotification.value = message;

    // Show browser notification if permitted
    if (Notification.permission === "granted") {
      new Notification(`Genesis: ${message.event_type}`, {
        body: message.payload?.message as string || "New notification",
        icon: "/favicon.ico",
      });
    }
  };

  const { state, messages, connect, disconnect, send, clearMessages } = useWebSocket(
    token,
    handleNewMessage,
  );

  const markAsRead = () => {
    unreadCount.value = 0;
  };

  const requestBrowserPermission = async () => {
    if ("Notification" in window) {
      const permission = await Notification.requestPermission();
      return permission === "granted";
    }
    return false;
  };

  return {
    state,
    messages,
    unreadCount,
    latestNotification,
    connect,
    disconnect,
    send,
    clearMessages,
    markAsRead,
    requestBrowserPermission,
  };
}
