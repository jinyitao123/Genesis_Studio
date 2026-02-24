import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { ComplianceRecord } from '@/types';

export function useComplianceStore() {
  return defineStore('compliance', () => {
    // State
    const complianceRecords = ref<ComplianceRecord[]>([]);
    const currentSubject = ref<string>('');
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Actions
    async function loadRecords(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const records = await apiGet<ComplianceRecord[]>('/api/compliance/records');
        complianceRecords.value = records;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load compliance records';
      } finally {
        loading.value = false;
      }
    }

    async function exportData(subjectId: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        currentSubject.value = subjectId;
        await apiPost('/api/compliance/export', { subject_id: subjectId });
        await loadRecords();
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Export failed';
        return false;
      } finally {
        loading.value = false;
      }
    }

    async function deleteData(subjectId: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        currentSubject.value = subjectId;
        await apiPost('/api/compliance/delete', { subject_id: subjectId });
        await loadRecords();
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Delete failed';
        return false;
      } finally {
        loading.value = false;
      }
    }

    function clear(): void {
      complianceRecords.value = [];
      currentSubject.value = '';
      error.value = null;
    }

    return {
      complianceRecords,
      currentSubject,
      loading,
      error,
      loadRecords,
      exportData,
      deleteData,
      clear,
    };
  })();
}
