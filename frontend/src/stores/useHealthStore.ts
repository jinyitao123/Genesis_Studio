import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiGet } from '@/api/client';
import type { HealthPayload } from '@/types';

export function useHealthStore() {
  return defineStore('health', () => {
    // State
    const queryHealth = ref<HealthPayload | null>(null);
    const commandHealth = ref<HealthPayload | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Actions
    async function loadHealth(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const [qh, ch] = await Promise.all([
          apiGet<HealthPayload>('/api/health'),
          apiGet<HealthPayload>('/health'),
        ]);
        queryHealth.value = qh;
        commandHealth.value = ch;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load health';
      } finally {
        loading.value = false;
      }
    }

    async function loadAll(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const [qh, ch] = await Promise.all([
          apiGet<HealthPayload>('/api/health').catch(() => ({ status: 'error', service: 'query-api' } as HealthPayload)),
          apiGet<HealthPayload>('/health').catch(() => ({ status: 'error', service: 'command-api' } as HealthPayload)),
        ]);
        queryHealth.value = qh;
        commandHealth.value = ch;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load health';
      } finally {
        loading.value = false;
      }
    }

    function clear(): void {
      queryHealth.value = null;
      commandHealth.value = null;
      error.value = null;
    }

    return {
      queryHealth,
      commandHealth,
      loading,
      error,
      loadHealth,
      loadAll,
      clear,
    };
  })();
}
