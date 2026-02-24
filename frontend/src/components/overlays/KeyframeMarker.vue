<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useTimelineStore } from '@/stores/useTimelineStore';
import type { TimelineKeyframe, Tick } from '@/types';

const props = defineProps<{
  // Keyframe to display (or will use store keyframes if not provided)
  keyframe?: TimelineKeyframe;
  // Tick position for this marker
  tick: Tick;
  // Total ticks for percentage calculation
  totalTicks: Tick;
  // Whether this is the currently active keyframe
  isActive?: boolean;
  // Whether to show expanded details
  showDetails?: boolean;
  // Marker size
  size?: 'small' | 'medium' | 'large';
  // Visual style variant
  variant?: 'default' | 'auto' | 'manual' | 'current';
}>();

const emit = defineEmits<{
  (event: 'click', keyframe: TimelineKeyframe): void;
  (event: 'doubleClick', keyframe: TimelineKeyframe): void;
  (event: 'rightClick', keyframe: TimelineKeyframe, event: MouseEvent): void;
  (event: 'hover', keyframe: TimelineKeyframe | null): void;
  (event: 'edit', keyframe: TimelineKeyframe): void;
  (event: 'delete', keyframe: TimelineKeyframe): void;
  (event: 'jumpTo', tick: Tick): void;
}>();

// Use timeline store
const timelineStore = useTimelineStore();

// Local state
const isHovered = ref(false);
const isEditing = ref(false);
const editLabel = ref('');

// Computed keyframe (from props or store)
const keyframe = computed(() => props.keyframe);

// Computed position percentage
const positionPercent = computed(() => {
  if (props.totalTicks === 0) return 0;
  return (props.tick / props.totalTicks) * 100;
});

// Computed style variant
const variantType = computed(() => {
  if (props.variant) return props.variant;
  if (props.isActive) return 'current';
  if (keyframe.value?.isAuto) return 'auto';
  return 'manual';
});

// Computed size class
const sizeClass = computed(() => props.size || 'medium');

// Computed icon
const icon = computed(() => {
  switch (variantType.value) {
    case 'auto': return '⚡';
    case 'current': return '▶';
    case 'manual': return '📌';
    default: return '●';
  }
});

// Computed color
const color = computed(() => {
  switch (variantType.value) {
    case 'auto': return '#8b5cf6'; // Purple
    case 'current': return '#10b981'; // Green
    case 'manual': return '#f59e0b'; // Amber
    default: return '#6b7280'; // Gray
  }
});

// Computed label
const displayLabel = computed(() => {
  if (keyframe.value?.label) {
    return keyframe.value.label;
  }
  if (variantType.value === 'auto') {
    return `Auto ${props.tick}`;
  }
  return `Tick ${props.tick}`;
});

// Format timestamp
const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '--:--:--';
  }
};

// Mouse handlers
const onClick = () => {
  if (keyframe.value) {
    emit('click', keyframe.value);
    emit('jumpTo', props.tick);
  }
};

const onDoubleClick = () => {
  if (keyframe.value) {
    emit('doubleClick', keyframe.value);
  }
};

const onRightClick = (event: MouseEvent) => {
  event.preventDefault();
  if (keyframe.value) {
    emit('rightClick', keyframe.value, event);
  }
};

const onMouseEnter = () => {
  isHovered.value = true;
  if (keyframe.value) {
    emit('hover', keyframe.value);
  }
};

const onMouseLeave = () => {
  isHovered.value = false;
  emit('hover', null);
};

// Edit handlers
const startEditing = () => {
  if (keyframe.value && !keyframe.value.isAuto) {
    isEditing.value = true;
    editLabel.value = keyframe.value.label;
  }
};

const saveEdit = () => {
  if (keyframe.value && editLabel.value.trim()) {
    timelineStore.updateKeyframe(keyframe.value.id, {
      label: editLabel.value.trim(),
    });
  }
  isEditing.value = false;
};

const cancelEdit = () => {
  isEditing.value = false;
};

// Delete handler
const deleteKeyframe = () => {
  if (keyframe.value) {
    timelineStore.removeKeyframe(keyframe.value.id);
    emit('delete', keyframe.value);
  }
};

// Computed metadata string
const metadataString = computed(() => {
  if (!keyframe.value?.metadata) return '';
  
  const entries = Object.entries(keyframe.value.metadata);
  if (entries.length === 0) return '';
  
  return entries
    .slice(0, 3)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).substring(0, 20) : v}`)
    .join(' • ');
});

// Keyboard shortcut hint
const shortcutHint = computed(() => {
  if (variantType.value === 'auto') return 'Auto-generated';
  return 'Double-click to edit';
});
</script>

<template>
  <div 
    class="keyframe-marker"
    :class="[
      sizeClass,
      variantType,
      { active: isActive, hovered: isHovered, editing: isEditing }
    ]"
    :style="{
      '--kf-color': color,
      '--kf-position': `${positionPercent}%`
    }"
    @click="onClick"
    @dblclick="onDoubleClick"
    @contextmenu="onRightClick"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <!-- Marker Pin -->
    <div class="marker-pin" :style="{ backgroundColor: color }">
      <span class="marker-icon">{{ icon }}</span>
    </div>
    
    <!-- Connector Line -->
    <div class="connector-line" :style="{ backgroundColor: color }"></div>
    
    <!-- Hover Card -->
    <div v-if="isHovered || isActive" class="hover-card">
      <div class="card-header">
        <span class="card-icon" :style="{ color: color }">{{ icon }}</span>
        <span class="card-label">{{ displayLabel }}</span>
        <span v-if="keyframe?.isAuto" class="auto-badge">AUTO</span>
      </div>
      
      <div class="card-info">
        <div class="info-row">
          <span class="info-label">Tick</span>
          <span class="info-value mono">{{ tick.toLocaleString() }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">时间</span>
          <span class="info-value">{{ formatTimestamp(keyframe?.timestamp || new Date().toISOString()) }}</span>
        </div>
        <div v-if="metadataString" class="info-row metadata">
          <span class="info-label">元数据</span>
          <span class="info-value truncate">{{ metadataString }}</span>
        </div>
      </div>
      
      <!-- Action Buttons -->
      <div v-if="!keyframe?.isAuto" class="card-actions">
        <button 
          v-if="!isEditing"
          class="action-btn edit-btn"
          @click.stop="startEditing"
          title="编辑标签"
        >
          ✏️
        </button>
        <button 
          class="action-btn jump-btn"
          @click.stop="onClick"
          title="跳转到此帧"
        >
          ⏭
        </button>
        <button 
          class="action-btn delete-btn"
          @click.stop="deleteKeyframe"
          title="删除关键帧"
        >
          🗑️
        </button>
      </div>
      
      <!-- Edit Form -->
      <div v-if="isEditing" class="edit-form" @click.stop>
        <input
          v-model="editLabel"
          type="text"
          class="edit-input"
          placeholder="输入标签..."
          @keydown.enter="saveEdit"
          @keydown.escape="cancelEdit"
          autofocus
        />
        <div class="edit-actions">
          <button class="edit-action-btn save" @click="saveEdit">✓</button>
          <button class="edit-action-btn cancel" @click="cancelEdit">✕</button>
        </div>
      </div>
      
      <!-- Shortcut Hint -->
      <div class="card-hint">
        {{ shortcutHint }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.keyframe-marker {
  position: absolute;
  left: var(--kf-position);
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 10;
  transition: transform 0.2s ease, z-index 0s 0.2s;
}

.keyframe-marker:hover,
.keyframe-marker.active,
.keyframe-marker.hovered {
  z-index: 20;
  transform: translateX(-50%) scale(1.1);
  transition: transform 0.2s ease;
}

/* Marker Pin */
.marker-pin {
  width: 24px;
  height: 24px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.marker-pin:hover {
  transform: rotate(-45deg) scale(1.15);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.25);
}

.marker-icon {
  transform: rotate(45deg);
  font-size: 12px;
  line-height: 1;
}

/* Size variants */
.keyframe-marker.small .marker-pin {
  width: 18px;
  height: 18px;
}

.keyframe-marker.small .marker-icon {
  font-size: 9px;
}

.keyframe-marker.large .marker-pin {
  width: 32px;
  height: 32px;
}

.keyframe-marker.large .marker-icon {
  font-size: 16px;
}

/* Connector Line */
.connector-line {
  width: 2px;
  height: 20px;
  margin-top: -2px;
}

/* Hover Card */
.hover-card {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 8px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  min-width: 180px;
  max-width: 240px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 100;
  cursor: default;
}

.hover-card::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid #e2e8f0;
}

.hover-card::after {
  content: '';
  position: absolute;
  top: -5px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid white;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.card-icon {
  font-size: 14px;
}

.card-label {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
}

.auto-badge {
  font-size: 9px;
  padding: 2px 6px;
  background: #f3e8ff;
  color: #7c3aed;
  border-radius: 4px;
  font-weight: 600;
}

/* Card Info */
.card-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.info-label {
  color: #64748b;
}

.info-value {
  color: #1e293b;
  font-weight: 500;
}

.info-value.mono {
  font-family: 'SF Mono', 'Consolas', monospace;
}

.info-row.metadata {
  border-top: 1px dashed #e2e8f0;
  padding-top: 6px;
  margin-top: 2px;
}

.info-value.truncate {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Card Actions */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.delete-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

/* Edit Form */
.edit-form {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.edit-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.edit-input:focus {
  border-color: #3b82f6;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 6px;
}

.edit-action-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 11px;
  border-radius: 4px;
  transition: background 0.2s;
}

.edit-action-btn.save:hover {
  background: #dcfce7;
  color: #16a34a;
}

.edit-action-btn.cancel:hover {
  background: #fef2f2;
  color: #dc2626;
}

/* Card Hint */
.card-hint {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid #f1f5f9;
  font-size: 10px;
  color: #94a3b8;
  text-align: center;
}

/* Variant Styles */
.keyframe-marker.auto .marker-pin {
  border: 2px solid white;
}

.keyframe-marker.current .marker-pin {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

/* Current tick indicator */
.keyframe-marker.current .connector-line {
  height: 30px;
  background: linear-gradient(to bottom, var(--kf-color), transparent);
}
</style>
