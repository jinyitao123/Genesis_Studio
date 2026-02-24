import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet } from '@/api/client';
import type { LineageAggregate } from '@/types';

export function useLineageStore() {
  return defineStore('lineage', () => {
    // State
    const lineageAggregate = ref<LineageAggregate | null>(null);
    const selectedTxnId = ref<string>('');
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Getters
    const hasLineage = computed(() => !!lineageAggregate.value);

    // Actions
    async function loadLineage(txnId: string): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        selectedTxnId.value = txnId;
        const data = await apiGet<LineageAggregate>(`/api/query/transactions/lineage/${txnId}/aggregate`);
        lineageAggregate.value = data;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load lineage';
      } finally {
        loading.value = false;
      }
    }

    function selectTransaction(txnId: string): void {
      selectedTxnId.value = txnId;
    }

    function clear(): void {
      lineageAggregate.value = null;
      selectedTxnId.value = '';
      error.value = null;
    }

    return {
      lineageAggregate,
      selectedTxnId,
      loading,
      error,
      hasLineage,
      loadLineage,
      selectTransaction,
      clear,
    };
  })();
}
