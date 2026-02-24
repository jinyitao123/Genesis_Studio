<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useCopilotStore, useStudioStore } from '@/stores';
import type { CopilotContext } from '@/types';

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: string;
  action?: () => void;
  category: 'navigation' | 'action' | 'ai' | 'system';
}

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
}>();

const copilotStore = useCopilotStore();
const studioStore = useStudioStore();
const router = useRouter();

const searchInput = ref<HTMLInputElement | null>(null);
const query = ref('');
const selectedIndex = ref(0);
const isLoading = ref(false);
const aiResponse = ref<string | null>(null);

const commands: CommandItem[] = [
  { id: 'nav-graph', label: '转到图谱', description: '打开图谱视图', icon: '📊', category: 'navigation', action: () => router.push('/graph') },
  { id: 'nav-timeline', label: '转到时间线', description: '打开时间线视图', icon: '⏱️', category: 'navigation', action: () => router.push('/timeline') },
  { id: 'nav-logic', label: '转到逻辑', description: '打开逻辑编排视图', icon: '🔧', category: 'navigation', action: () => router.push('/logic') },
  { id: 'nav-lineage', label: '转到追溯', description: '打开血缘追溯视图', icon: '🔗', category: 'navigation', action: () => router.push('/lineage') },
  { id: 'nav-inspector', label: '转到检查器', description: '打开检查器视图', icon: '🔍', category: 'navigation', action: () => router.push('/inspector') },
  { id: 'toggle-mode', label: '切换模式', description: '在草稿/仿真模式间切换', icon: '🔄', category: 'system', action: () => studioStore.toggleMode() },
  { id: 'save-changes', label: '保存变更', description: '保存所有未保存的更改', icon: '💾', category: 'system', action: () => studioStore.saveChanges() },
  { id: 'validate', label: '验证本体', description: '运行本体验证', icon: '✅', category: 'system', action: () => validateOntology() },
  { id: 'ai-create-entity', label: 'AI: 创建实体', description: '使用 AI 助手创建新实体', icon: '🤖', category: 'ai' },
  { id: 'ai-generate-logic', label: 'AI: 生成逻辑', description: '使用 AI 助手生成逻辑规则', icon: '⚡', category: 'ai' },
  { id: 'ai-analyze', label: 'AI: 分析仿真', description: '使用 AI 分析当前仿真状态', icon: '📈', category: 'ai' },
  { id: 'action-fire', label: '动作: 开火', description: '执行 ACT_FIRE 动作', icon: '🔥', category: 'action' },
  { id: 'action-move', label: '动作: 移动', description: '执行 ACT_MOVE 动作', icon: '🚀', category: 'action' },
  { id: 'action-repair', label: '动作: 维修', description: '执行 ACT_REPAIR 动作', icon: '🔧', category: 'action' },
];

const filteredCommands = computed(() => {
  if (!query.value.trim()) {
    return commands.slice(0, 10);
  }
  
  const lowerQuery = query.value.toLowerCase();
  return commands
    .filter(cmd => 
      cmd.label.toLowerCase().includes(lowerQuery) ||
      cmd.description.toLowerCase().includes(lowerQuery) ||
      cmd.category.toLowerCase().includes(lowerQuery)
    )
    .slice(0, 10);
});

const groupedCommands = computed(() => {
  const groups: Record<string, CommandItem[]> = {
    navigation: [],
    action: [],
    ai: [],
    system: [],
  };
  
  filteredCommands.value.forEach(cmd => {
    if (groups[cmd.category]) {
      groups[cmd.category].push(cmd);
    }
  });
  
  return Object.entries(groups).filter(([_, items]) => items.length > 0);
});

async function handleAiQuery() {
  if (!query.value.trim() || query.value.length < 3) return;
  
  isLoading.value = true;
  
  try {
    const context: CopilotContext = {
      selectedNodes: [],
      currentView: studioStore.activeTab,
      tick: studioStore.selectedTick,
    };
    
    const response = await copilotStore.runCopilot('general', query.value, context);
    aiResponse.value = response.plan?.join('\n') || 'AI 已处理您的请求';
  } catch (e) {
    aiResponse.value = 'AI 处理失败，请重试';
  } finally {
    isLoading.value = false;
  }
}

async function validateOntology() {
  // TODO: Implement actual validation
  console.log('Validating ontology...');
  emit('update:modelValue', false);
}

function executeCommand(cmd: CommandItem) {
  if (cmd.action) {
    cmd.action();
  } else if (cmd.category === 'ai') {
    handleAiQuery();
  }
  close();
}

function close() {
  emit('update:modelValue', false);
  query.value = '';
  aiResponse.value = null;
  selectedIndex.value = 0;
}

function handleKeydown(e: KeyboardEvent) {
  if (!props.modelValue) return;
  
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCommands.value.length - 1);
      break;
    case 'ArrowUp':
      e.preventDefault();
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0);
      break;
    case 'Enter':
      e.preventDefault();
      if (filteredCommands.value[selectedIndex.value]) {
        executeCommand(filteredCommands.value[selectedIndex.value]);
      }
      break;
    case 'Escape':
      e.preventDefault();
      close();
      break;
  }
}

watch(() => props.modelValue, async (isOpen) => {
  if (isOpen) {
    await nextTick();
    searchInput.value?.focus();
    query.value = '';
    selectedIndex.value = 0;
    aiResponse.value = null;
  }
});

watch(query, () => {
  selectedIndex.value = 0;
});

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="command-palette-overlay" @click.self="close">
        <div class="command-palette">
          <div class="palette-header">
            <span class="search-icon">🔍</span>
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              placeholder="输入命令或问题..."
              class="search-input"
            />
            <span class="shortcut-hint">ESC 关闭</span>
          </div>
          
          <div class="palette-content">
            <div v-if="aiResponse" class="ai-response">
              <div class="ai-header">
                <span class="ai-icon">🤖</span>
                <span>AI 建议</span>
              </div>
              <pre>{{ aiResponse }}</pre>
            </div>
            
            <div v-else class="commands-list">
              <div 
                v-for="(group, groupIndex) in groupedCommands" 
                :key="group[0]"
                class="command-group"
              >
                <div class="group-title">{{ group[0] }}</div>
                <div 
                  v-for="(cmd, cmdIndex) in group[1]" 
                  :key="cmd.id"
                  class="command-item"
                  :class="{ 
                    selected: filteredCommands.indexOf(cmd) === selectedIndex 
                  }"
                  @click="executeCommand(cmd)"
                  @mouseenter="selectedIndex = filteredCommands.indexOf(cmd)"
                >
                  <span class="cmd-icon">{{ cmd.icon }}</span>
                  <div class="cmd-info">
                    <span class="cmd-label">{{ cmd.label }}</span>
                    <span class="cmd-desc">{{ cmd.description }}</span>
                  </div>
                </div>
              </div>
              
              <div v-if="filteredCommands.length === 0" class="no-results">
                <span>未找到命令</span>
                <span class="hint">尝试输入 AI 请求获取帮助</span>
              </div>
            </div>
          </div>
          
          <div class="palette-footer">
            <span class="footer-hint">
              <kbd>↑</kbd><kbd>↓</kbd> 导航
            </span>
            <span class="footer-hint">
              <kbd>↵</kbd> 执行
            </span>
            <span class="footer-hint">
              <kbd>Ctrl</kbd><kbd>K</kbd> 打开
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts">
export default {
  name: 'CommandPalette'
};
</script>

<style scoped>
.command-palette-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: 9999;
}

.command-palette {
  width: 600px;
  max-width: 90vw;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.palette-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.search-icon {
  font-size: 18px;
  opacity: 0.5;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 16px;
  outline: none;
  color: #1f2937;
}

.search-input::placeholder {
  color: #9ca3af;
}

.shortcut-hint {
  font-size: 12px;
  color: #9ca3af;
  background: #e5e7eb;
  padding: 4px 8px;
  border-radius: 4px;
}

.palette-content {
  max-height: 400px;
  overflow-y: auto;
}

.ai-response {
  padding: 16px;
  background: #f0f9ff;
  border-bottom: 1px solid #bae6fd;
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #0369a1;
}

.ai-response pre {
  margin: 0;
  font-family: inherit;
  font-size: 14px;
  white-space: pre-wrap;
  color: #1e40af;
}

.commands-list {
  padding: 8px;
}

.command-group {
  margin-bottom: 8px;
}

.group-title {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  padding: 8px 8px 4px;
}

.command-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.command-item:hover,
.command-item.selected {
  background: #f3f4f6;
}

.command-item.selected {
  background: #dbeafe;
}

.cmd-icon {
  font-size: 18px;
}

.cmd-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cmd-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.cmd-desc {
  font-size: 12px;
  color: #6b7280;
}

.no-results {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}

.no-results .hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #9ca3af;
}

.palette-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.footer-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.footer-hint kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: #e5e7eb;
  border-radius: 4px;
  font-family: inherit;
  font-size: 11px;
  color: #4b5563;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
