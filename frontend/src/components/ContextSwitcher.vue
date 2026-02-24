<script setup lang="ts">
import { computed } from 'vue';
import { useStudioStore } from '@/stores';
import type { StudioMode } from '@/types';

const studioStore = useStudioStore();

const currentMode = computed({
  get: () => studioStore.studioMode,
  set: (value: StudioMode) => studioStore.setStudioMode(value),
});

const modeLabels: Record<StudioMode, string> = {
  draft: '草稿',
  simulation: '仿真',
};

const modeColors: Record<StudioMode, string> = {
  draft: '#f59e0b',
  simulation: '#10b981',
};

const modeIcons: Record<StudioMode, string> = {
  draft: '✏️',
  simulation: '▶️',
};

const toggleMode = () => {
  studioStore.toggleMode();
};
</script>

<template>
  <div class="context-switcher" :class="currentMode">
    <button 
      class="mode-toggle"
      :class="{ active: currentMode === 'draft' }"
      @click="currentMode = 'draft'"
    >
      <span class="icon">{{ modeIcons.draft }}</span>
      <span class="label">{{ modeLabels.draft }}</span>
    </button>
    
    <div class="toggle-track">
      <div 
        class="toggle-indicator"
        :class="currentMode"
      ></div>
    </div>
    
    <button 
      class="mode-toggle"
      :class="{ active: currentMode === 'simulation' }"
      @click="currentMode = 'simulation'"
    >
      <span class="icon">{{ modeIcons.simulation }}</span>
      <span class="label">{{ modeLabels.simulation }}</span>
    </button>
  </div>
</template>

<script lang="ts">
export default {
  name: 'ContextSwitcher'
};
</script>

<style scoped>
.context-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 999px;
  padding: 4px;
}

.mode-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 999px;
  transition: all 0.2s ease;
}

.mode-toggle:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.mode-toggle.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.icon {
  font-size: 14px;
}

.toggle-track {
  width: 36px;
  height: 20px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  position: relative;
  cursor: pointer;
}

.toggle-indicator {
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: all 0.2s ease;
}

.toggle-indicator.draft {
  left: 2px;
  background: #f59e0b;
}

.toggle-indicator.simulation {
  left: 18px;
  background: #10b981;
}

.context-switcher.simulation {
  background: rgba(16, 185, 129, 0.2);
}

.context-switcher.simulation .toggle-indicator {
  background: #10b981;
}
</style>
