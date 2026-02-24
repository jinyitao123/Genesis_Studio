import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet } from '@/api/client';
import type { EventPayload, TransactionPayload } from '@/types';

export function useEventStore() {
  return defineStore('events', () => {
    // State
    const events = ref<EventPayload[]>([]);
    const transactions = ref<TransactionPayload[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);

    function asArray<T>(value: unknown): T[] {
      return Array.isArray(value) ? (value as T[]) : [];
    }

    // Getters
    const latestEvents = computed(() => asArray<EventPayload>(events.value).slice(0, 1000));
    const eventCount = computed(() => asArray<EventPayload>(events.value).length);
    const transactionCount = computed(() => asArray<TransactionPayload>(transactions.value).length);
    const actionTypes = computed(() => {
      const actions = new Set(asArray<EventPayload>(events.value).map(e => e.action_id));
      return Array.from(actions);
    });

    // Actions
    async function loadEvents(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const evts = await apiGet<EventPayload[]>('/api/query/events');
        events.value = asArray<EventPayload>(evts);
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load events';
      } finally {
        loading.value = false;
      }
    }

    async function loadTransactions(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const txns = await apiGet<TransactionPayload[]>('/api/query/transactions');
        transactions.value = asArray<TransactionPayload>(txns);
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load transactions';
      } finally {
        loading.value = false;
      }
    }

    async function loadAll(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const [evts, txns] = await Promise.all([
          apiGet<EventPayload[]>('/api/query/events').catch(() => []),
          apiGet<TransactionPayload[]>('/api/query/transactions').catch(() => []),
        ]);
        events.value = asArray<EventPayload>(evts);
        transactions.value = asArray<TransactionPayload>(txns);
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load data';
      } finally {
        loading.value = false;
      }
    }

    function addEvent(event: EventPayload): void {
      if (!Array.isArray(events.value)) {
        events.value = [];
      }
      events.value.unshift(event);
      // Keep only last 1000
      if (events.value.length > 1000) {
        events.value = events.value.slice(0, 1000);
      }
    }

    function addTransaction(txn: TransactionPayload): void {
      if (!Array.isArray(transactions.value)) {
        transactions.value = [];
      }
      transactions.value.unshift(txn);
    }

    function clear(): void {
      events.value = [];
      transactions.value = [];
      error.value = null;
    }

    return {
      events,
      transactions,
      loading,
      error,
      latestEvents,
      eventCount,
      transactionCount,
      actionTypes,
      loadEvents,
      loadTransactions,
      loadAll,
      addEvent,
      addTransaction,
      clear,
    };
  })();
}
