import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { 
  CopilotRouteResponse, 
  CopilotContext,
  TabId,
  Tick 
} from '@/types';

export function useCopilotStore() {
  return defineStore('copilot', () => {
    // State
    const intent = ref<string>('general');
    const prompt = ref<string>('');
    const result = ref<CopilotRouteResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Actions
    async function runCopilot(
      intentValue: string,
      promptValue: string,
      context: CopilotContext
    ): Promise<CopilotRouteResponse | null> {
      loading.value = true;
      error.value = null;
      try {
        intent.value = intentValue;
        prompt.value = promptValue;
        
        result.value = await apiPost<CopilotRouteResponse>(
          '/api/copilot/route',
          {
            intent: intentValue,
            prompt: promptValue,
            context,
          }
        );
        return result.value;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Copilot call failed';
        return null;
      } finally {
        loading.value = false;
      }
    }

    function classifyIntent(content: string): string {
      const lowered = content.toLowerCase();
      if (lowered.includes('创建') || lowered.includes('添加') || lowered.includes('生成') || 
          lowered.includes('ontology') || lowered.includes('schema')) {
        return 'ontology';
      }
      if (lowered.includes('规则') || lowered.includes('逻辑') || lowered.includes('动作') || 
          lowered.includes('action') || lowered.includes('rule')) {
        return 'logic';
      }
      if (lowered.includes('批量') || lowered.includes('填充') || lowered.includes('populate') || 
          lowered.includes('seed')) {
        return 'workflow';
      }
      if (lowered.includes('分析') || lowered.includes('查询') || lowered.includes('统计') || 
          lowered.includes('analytics') || lowered.includes('query')) {
        return 'data';
      }
      return 'general';
    }

    function clear(): void {
      intent.value = '';
      prompt.value = '';
      result.value = null;
      error.value = null;
    }

    return {
      intent,
      prompt,
      result,
      loading,
      error,
      runCopilot,
      classifyIntent,
      clear,
    };
  })();
}
