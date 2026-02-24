import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { 
  TabId, 
  StudioMode, 
  ActionField, 
  DispatchDryRunResponse,
  Tick,
  ObjectTypeDefinition,
  GraphNodePayload,
  GraphEdgePayload
} from '@/types';

export function useStudioStore() {
  return defineStore('studio', () => {
    // State
    const activeTab = ref<TabId>('graph');
    const studioMode = ref<StudioMode>('draft');
    const selectedTick = ref<Tick>(0);
    const busy = ref(false);
    const error = ref<string | null>(null);
    const dryRun = ref<DispatchDryRunResponse | null>(null);
    
    // Dirty State tracking
    const isDirty = ref(false);
    const dirtyItems = ref<Set<string>>(new Set());
    const lastSavedAt = ref<Date | null>(null);
    const pendingChanges = ref<Record<string, unknown>>({});
    let dirtyTimeout: ReturnType<typeof setTimeout> | null = null;
    
    // Default action schema for demo
    const defaultActionSchema: ActionField[] = [
      {
        name: 'action_id',
        label: '动作 ID',
        input: 'select',
        required: true,
        options: ['ACT_SELF_DESTRUCT', 'ACT_MOVE', 'ACT_REPAIR', 'ACT_ATTACK'],
        defaultValue: 'ACT_SELF_DESTRUCT',
      },
      { name: 'source_id', label: '源实体', input: 'text', required: true, defaultValue: 'entity-1' },
      { name: 'target_id', label: '目标实体', input: 'text', required: true, defaultValue: 'entity-2' },
      { name: 'damage', label: '伤害值', input: 'number', required: true, defaultValue: '50' },
    ];
    
    const actionSchema = ref<ActionField[]>(defaultActionSchema);

    // Getters
    const isSimulationMode = computed(() => studioMode.value === 'simulation');
    const canEdit = computed(() => studioMode.value === 'draft');
    const tickProgress = computed(() => selectedTick.value + 1);
    const hasPendingChanges = computed(() => dirtyItems.value.size > 0);
    const dirtyCount = computed(() => dirtyItems.value.size);

    // Dirty State actions
    function markDirty(itemId: string, change?: Record<string, unknown>): void {
      if (!dirtyItems.value.has(itemId)) {
        dirtyItems.value.add(itemId);
        isDirty.value = true;
      }
      
      if (change) {
        pendingChanges.value[itemId] = change;
      }
      
      // Auto-save after 30 seconds of inactivity
      scheduleAutoSave();
    }

    function markClean(itemId: string): void {
      dirtyItems.value.delete(itemId);
      delete pendingChanges.value[itemId];
      
      if (dirtyItems.value.size === 0) {
        isDirty.value = false;
        lastSavedAt.value = new Date();
      }
    }

    function clearAllDirty(): void {
      dirtyItems.value.clear();
      pendingChanges.value = {};
      isDirty.value = false;
      lastSavedAt.value = new Date();
    }

    function scheduleAutoSave(): void {
      if (dirtyTimeout) {
        clearTimeout(dirtyTimeout);
      }
      
      dirtyTimeout = setTimeout(() => {
        autoSaveChanges();
      }, 30000); // 30 seconds
    }

    async function autoSaveChanges(): Promise<void> {
      if (dirtyItems.value.size === 0) return;
      
      busy.value = true;
      try {
        // TODO: Implement actual auto-save to backend
        console.log('Auto-saving changes:', pendingChanges.value);
        lastSavedAt.value = new Date();
        dirtyItems.value.clear();
        pendingChanges.value = {};
        isDirty.value = false;
      } catch (e) {
        console.error('Auto-save failed:', e);
      } finally {
        busy.value = false;
      }
    }

    async function saveChanges(): Promise<boolean> {
      if (!hasPendingChanges.value) return true;
      
      busy.value = true;
      error.value = null;
      
      try {
        await autoSaveChanges();
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Save failed';
        return false;
      } finally {
        busy.value = false;
      }
    }

    // Actions
    function setActiveTab(tab: TabId): void {
      activeTab.value = tab;
    }

    function setStudioMode(mode: StudioMode): void {
      studioMode.value = mode;
    }

    function toggleMode(): void {
      studioMode.value = studioMode.value === 'draft' ? 'simulation' : 'draft';
    }

    function setSelectedTick(tick: Tick): void {
      selectedTick.value = Math.max(0, tick);
    }

    function incrementTick(delta: number = 1): void {
      selectedTick.value += delta;
    }

    async function submitDraftAction(values: Record<string, string>): Promise<boolean> {
      busy.value = true;
      error.value = null;
      try {
        dryRun.value = await apiPost<DispatchDryRunResponse>(
          '/api/command/dispatch/dry-run',
          {
            action_id: values.action_id,
            source_id: values.source_id,
            target_id: values.target_id,
            payload: {
              damage: Number(values.damage),
            },
          }
        );
        return dryRun.value.allowed;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Action dry-run failed';
        return false;
      } finally {
        busy.value = false;
      }
    }

    function clearError(): void {
      error.value = null;
    }

    function reset(): void {
      activeTab.value = 'graph';
      studioMode.value = 'draft';
      selectedTick.value = 0;
      busy.value = false;
      error.value = null;
      dryRun.value = null;
      clearAllDirty();
    }

    return {
      activeTab,
      studioMode,
      selectedTick,
      busy,
      error,
      dryRun,
      actionSchema,
      isSimulationMode,
      canEdit,
      tickProgress,
      isDirty,
      dirtyItems,
      lastSavedAt,
      pendingChanges,
      hasPendingChanges,
      dirtyCount,
      setActiveTab,
      setStudioMode,
      toggleMode,
      setSelectedTick,
      incrementTick,
      submitDraftAction,
      clearError,
      reset,
      markDirty,
      markClean,
      clearAllDirty,
      saveChanges,
      autoSaveChanges,
    };
  })();
}
