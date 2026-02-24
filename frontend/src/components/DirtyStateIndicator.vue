<script setup lang="ts">
import { computed } from 'vue';
import { useStudioStore } from '@/stores';

const studioStore = useStudioStore();

const isDirty = computed(() => studioStore.isDirty);
const dirtyCount = computed(() => studioStore.dirtyCount);
const lastSavedAt = computed(() => studioStore.lastSavedAt);

const formattedLastSaved = computed(() => {
  if (!lastSavedAt.value) return '未保存';
  return lastSavedAt.value.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
});

const statusText = computed(() => {
  if (isDirty.value) {
    return `${dirtyCount.value} 项变更待保存`;
  }
  return '已保存';
});
</script>

<template>
  <div class="dirty-state-indicator" :class="{ dirty: isDirty }">
    <div class="indicator-dot" :class="{ pulse: isDirty }">
      <span v-if="isDirty" class="count">{{ dirtyCount }}</span>
      <span v-else class="checkmark">✓</span>
    </div>
    
    <div class="status-info">
      <span class="status-text">{{ statusText }}</span>
      <span v-if="!isDirty" class="last-saved">{{ formattedLastSaved }}</span>
    </div>
    
    <button 
      v-if="isDirty" 
      class="save-btn"
      @click="studioStore.saveChanges()"
    >
      保存
    </button>
  </div>
</template>

<script lang="ts">
export default {
  name: 'DirtyStateIndicator'
};
</script>

<style scoped>
.dirty-state-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.dirty-state-indicator.dirty {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.indicator-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  font-size: 11px;
  font-weight: 600;
}

.indicator-dot.pulse {
  background: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(245, 158, 11, 0);
  }
}

.checkmark {
  font-size: 12px;
}

.count {
  font-size: 10px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.last-saved {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.save-btn {
  padding: 4px 10px;
  border: none;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.save-btn:hover {
  background: linear-gradient(135deg, #d97706, #b45309);
  transform: translateY(-1px);
}

.save-btn:active {
  transform: translateY(0);
}
</style>
