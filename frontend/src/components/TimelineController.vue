<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useTimelineStore } from '@/stores/useTimelineStore';
import type { Tick, EventPayload, TimelineKeyframe } from '@/types';

const props = defineProps<{
  modelValue: Tick;
  events: EventPayload[];
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: Tick): void;
  (event: 'jumpToTick', tick: Tick): void;
  (event: 'addKeyframe', tick: Tick): void;
  (event: 'removeKeyframe', id: string): void;
  (event: 'toggleGhostVisibility'): void;
  (event: 'togglePredictionVisibility'): void;
}>();

// Use timeline store
const timelineStore = useTimelineStore();

// Local state
const fineMode = ref(false);
const speedDropdownOpen = ref(false);
const keyframeDropdownOpen = ref(false);

// Sync with props
watch(() => props.modelValue, (newTick) => {
  if (newTick !== timelineStore.currentTick) {
    timelineStore.goToTick(newTick);
  }
});

watch(() => timelineStore.currentTick, (newTick) => {
  emit('update:modelValue', newTick);
});

// Sync store keyframes with events
watch(() => props.events, (newEvents) => {
  if (timelineStore.totalKeyframes === 0) {
    newEvents.forEach((event, index) => {
      if (index % 10 === 0) {
        timelineStore.addAutoKeyframe(index);
      }
    });
  }
}, { immediate: true });

// Computed
const bufferedEvents = computed(() => props.events.slice(-1000));
const maxTick = computed(() => Math.max(bufferedEvents.value.length - 1, timelineStore.maxTick, 0));

// Keyframes from store or derived from events
const keyframes = computed(() => {
  if (timelineStore.totalKeyframes > 0) {
    return timelineStore.keyframes;
  }
  return bufferedEvents.value
    .map((item, index) => ({
      id: `event_${item.event_id}`,
      tick: index,
      label: item.action_id,
      timestamp: item.created_at || new Date().toISOString(),
      metadata: { event_id: item.event_id },
      isAuto: index % 10 === 0,
    }))
    .filter((_, index) => index % 10 === 0)
    .slice(-20);
});

// Ghost frames from store
const ghostFrames = computed(() => timelineStore.currentGhostFrames);

// Prediction frames from store
const predictionFrames = computed(() => timelineStore.currentPredictionFrames);

// Buffer usage percentage
const bufferUsagePercent = computed(() => timelineStore.bufferUsage.percentage);

// Current keyframe info
const currentKeyframe = computed(() => timelineStore.keyframeAtCurrentTick);

// Nearby keyframes
const nearbyKeyframes = computed(() => timelineStore.nearbyKeyframes.slice(0, 5));

// Speed options
const speedOptions = [0.25, 0.5, 1, 2, 4, 8];

// Tick update
const updateTick = (value: number) => {
  const clamped = Math.min(Math.max(value, 0), maxTick.value);
  timelineStore.goToTick(clamped);
  emit('update:modelValue', clamped);
};

// Playback controls
const togglePlay = () => {
  timelineStore.togglePlayback();
};

const stop = () => {
  timelineStore.stop();
};

const stepTick = (direction: 1 | -1) => {
  const delta = fineMode.value ? 1 : Math.ceil(timelineStore.playbackSpeed);
  updateTick(timelineStore.currentTick + direction * delta);
};

const goToStart = () => {
  timelineStore.goToStart();
  emit('update:modelValue', 0);
};

const goToEnd = () => {
  timelineStore.goToEnd();
  emit('update:modelValue', maxTick.value);
};

// Speed control
const setSpeed = (speed: number) => {
  timelineStore.setSpeed(speed);
  speedDropdownOpen.value = false;
};

// Keyframe actions
const jumpToKeyframe = (kf: TimelineKeyframe) => {
  updateTick(kf.tick);
  keyframeDropdownOpen.value = false;
  emit('jumpToTick', kf.tick);
};

const addManualKeyframe = () => {
  const kf = timelineStore.addKeyframe(
    timelineStore.currentTick,
    `Manual ${timelineStore.currentTick}`,
    { manual: true }
  );
  emit('addKeyframe', kf.tick);
};

const removeKeyframeById = (id: string) => {
  timelineStore.removeKeyframe(id);
  emit('removeKeyframe', id);
};

// Ghost/Prediction visibility toggles
const toggleGhosts = () => {
  timelineStore.showGhosts = !timelineStore.showGhosts;
  emit('toggleGhostVisibility');
};

const togglePredictions = () => {
  timelineStore.showPredictions = !timelineStore.showPredictions;
  emit('togglePredictionVisibility');
};

// Keyboard controls
const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Shift') {
    fineMode.value = true;
  }
  if (event.key === ' ' && event.target === document.body) {
    event.preventDefault();
    togglePlay();
  }
  if (event.key === 'Home') {
    goToStart();
  }
  if (event.key === 'End') {
    goToEnd();
  }
};

const onKeyUp = (event: KeyboardEvent) => {
  if (event.key === 'Shift') {
    fineMode.value = false;
  }
};

// Tick buffer recording
const recordCurrentTick = () => {
  timelineStore.recordTick(timelineStore.currentTick);
};

// Lifecycle
onMounted(() => {
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('keyup', onKeyUp);
});

onBeforeUnmount(() => {
  timelineStore.pause();
  window.removeEventListener('keydown', onKeyDown);
  window.removeEventListener('keyup', onKeyUp);
});

// Format tick for display
const formatTick = (tick: Tick): string => {
  return tick.toLocaleString();
};

// Get keyframe label
const getKeyframeLabel = (kf: TimelineKeyframe): string => {
  return kf.label || `Tick ${kf.tick}`;
};
</script>

<template>
  <section class="timeline-controller">
    <!-- Header -->
    <header class="timeline-header">
      <h3>时间线控制器</h3>
      <div class="header-controls">
        <span class="mode-badge" :class="{ active: fineMode }">
          {{ fineMode ? '精细' : '快速' }}
        </span>
        <span class="tick-display">
          Tick {{ formatTick(timelineStore.currentTick) }}
        </span>
      </div>
    </header>

    <!-- Buffer Usage Indicator -->
    <div class="buffer-indicator" v-if="bufferUsagePercent > 0">
      <div class="buffer-bar">
        <div 
          class="buffer-fill" 
          :style="{ width: `${bufferUsagePercent}%` }"
        ></div>
      </div>
      <span class="buffer-text">
        Buffer: {{ timelineStore.bufferUsage.used }}/{{ timelineStore.bufferUsage.capacity }}
      </span>
    </div>

    <!-- Main Controls -->
    <div class="controls">
      <button type="button" class="control-btn" @click="goToStart" title="跳转到开始">
        ⏮
      </button>
      <button type="button" class="control-btn" @click="stepTick(-1)" title="上一帧">
        ◀
      </button>
      <button 
        type="button" 
        class="control-btn play-btn" 
        @click="togglePlay"
        :class="{ playing: timelineStore.isPlaying }"
        :title="timelineStore.isPlaying ? '暂停' : '播放'"
      >
        {{ timelineStore.isPlaying ? '⏸' : '▶' }}
      </button>
      <button type="button" class="control-btn" @click="stepTick(1)" title="下一帧">
        ▶
      </button>
      <button type="button" class="control-btn" @click="goToEnd" title="跳转到结束">
        ⏭
      </button>
      <button type="button" class="control-btn" @click="stop" title="停止">
        ⏹
      </button>
    </div>

    <!-- Timeline Slider -->
    <div class="slider-container">
      <input
        type="range"
        :min="0"
        :max="maxTick"
        :value="timelineStore.currentTick"
        @input="updateTick(Number(($event.target as HTMLInputElement).value))"
        class="timeline-slider"
      />
      <div class="slider-labels">
        <span>0</span>
        <span>{{ formatTick(maxTick) }}</span>
      </div>
    </div>

    <!-- Progress Bar with Keyframes -->
    <div class="progress-track">
      <div 
        class="progress-fill"
        :style="{ width: `${timelineStore.tickProgress.percentage}%` }"
      ></div>
      
      <!-- Keyframe markers on progress bar -->
      <div
        v-for="kf in nearbyKeyframes"
        :key="kf.id"
        class="keyframe-marker"
        :class="{ auto: kf.isAuto, current: kf.tick === timelineStore.currentTick }"
        :style="{ left: `${(kf.tick / maxTick) * 100}%` }"
        :title="kf.label"
        @click="jumpToKeyframe(kf)"
      ></div>
    </div>

    <!-- Secondary Controls Row -->
    <div class="secondary-controls">
      <!-- Speed Control -->
      <div class="control-group">
        <label>速度</label>
        <div class="speed-dropdown" :class="{ open: speedDropdownOpen }">
          <button 
            type="button" 
            class="dropdown-toggle"
            @click="speedDropdownOpen = !speedDropdownOpen"
          >
            {{ timelineStore.playbackSpeed }}x
          </button>
          <div class="dropdown-menu" v-if="speedDropdownOpen">
            <button
              v-for="speed in speedOptions"
              :key="speed"
              type="button"
              class="dropdown-item"
              :class="{ active: timelineStore.playbackSpeed === speed }"
              @click="setSpeed(speed)"
            >
              {{ speed }}x
            </button>
          </div>
        </div>
      </div>

      <!-- Keyframe Actions -->
      <div class="control-group">
        <label>关键帧</label>
        <div class="keyframe-dropdown" :class="{ open: keyframeDropdownOpen }">
          <button 
            type="button" 
            class="dropdown-toggle"
            @click="keyframeDropdownOpen = !keyframeDropdownOpen"
          >
            {{ currentKeyframe ? '编辑' : '添加' }}
          </button>
          <div class="dropdown-menu" v-if="keyframeDropdownOpen">
            <button type="button" class="dropdown-item" @click="addManualKeyframe">
              + 在当前帧添加
            </button>
            <div class="dropdown-divider" v-if="keyframes.length > 0"></div>
            <button
              v-for="kf in keyframes.slice(0, 10)"
              :key="kf.id"
              type="button"
              class="dropdown-item"
              @click="jumpToKeyframe(kf)"
            >
              {{ getKeyframeLabel(kf) }} (Tick {{ kf.tick }})
            </button>
          </div>
        </div>
      </div>

      <!-- Visibility Toggles -->
      <div class="control-group">
        <label>显示</label>
        <div class="toggle-buttons">
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: timelineStore.showGhosts }"
            @click="toggleGhosts"
            title="显示残影"
          >
            👻
          </button>
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: timelineStore.showPredictions }"
            @click="togglePredictions"
            title="显示预测"
          >
            🔮
          </button>
        </div>
      </div>

      <!-- Buffer Actions -->
      <div class="control-group">
        <label>缓冲区</label>
        <button type="button" class="action-btn" @click="recordCurrentTick" title="记录当前tick">
          💾
        </button>
      </div>
    </div>

    <!-- Info Panels -->
    <div class="info-panels">
      <!-- Current Keyframe Info -->
      <div class="info-panel" v-if="currentKeyframe">
        <h4>📌 当前关键帧</h4>
        <div class="keyframe-details">
          <span class="kf-label">{{ currentKeyframe.label }}</span>
          <span class="kf-meta">
            Tick {{ currentKeyframe.tick }} · {{ currentKeyframe.isAuto ? '自动' : '手动' }}
          </span>
          <span class="kf-time">{{ currentKeyframe.timestamp }}</span>
        </div>
      </div>

      <!-- Ghost Frame Info -->
      <div class="info-panel" v-if="timelineStore.showGhosts && ghostFrames.length > 0">
        <h4>👻 残影 ({{ ghostFrames.length }})</h4>
        <div class="ghost-list">
          <span 
            v-for="gf in ghostFrames.slice(0, 5)" 
            :key="gf.tick"
            class="ghost-badge"
          >
            T{{ gf.tick }} ({{ (gf.opacity * 100).toFixed(0) }}%)
          </span>
          <span v-if="ghostFrames.length > 5" class="more-badge">
            +{{ ghostFrames.length - 5 }} 更多
          </span>
        </div>
      </div>

      <!-- Prediction Frame Info -->
      <div class="info-panel" v-if="timelineStore.showPredictions && predictionFrames.length > 0">
        <h4>🔮 预测 ({{ predictionFrames.length }})</h4>
        <div class="prediction-list">
          <span 
            v-for="pf in predictionFrames.slice(0, 3)" 
            :key="pf.tick"
            class="prediction-badge"
            :class="{ high: pf.confidence >= 0.9, medium: pf.confidence >= 0.7 }"
          >
            T{{ pf.tick }} {{ (pf.confidence * 100).toFixed(0) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- Keyframe Strip -->
    <div class="keyframe-strip" v-if="keyframes.length > 0">
      <button
        v-for="kf in keyframes"
        :key="kf.id"
        type="button"
        class="keyframe-chip"
        :class="{ 
          auto: kf.isAuto, 
          current: kf.tick === timelineStore.currentTick 
        }"
        @click="jumpToKeyframe(kf)"
      >
        <span class="kf-icon">{{ kf.isAuto ? '⚡' : '📌' }}</span>
        <span class="kf-name">{{ getKeyframeLabel(kf) }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.timeline-controller {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

/* Header */
.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #e2e8f0;
  color: #64748b;
  font-weight: 600;
}

.mode-badge.active {
  background: #3b82f6;
  color: white;
}

.tick-display {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  font-family: 'SF Mono', 'Consolas', monospace;
}

/* Buffer Indicator */
.buffer-indicator {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.buffer-bar {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.buffer-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #84cc16);
  transition: width 0.3s ease;
}

.buffer-text {
  font-size: 10px;
  color: #64748b;
}

/* Main Controls */
.controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.control-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #cbd5e1;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.control-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.play-btn {
  width: 44px;
  height: 44px;
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
  font-size: 16px;
}

.play-btn:hover {
  background: #2563eb;
}

.play-btn.playing {
  background: #f59e0b;
  border-color: #f59e0b;
}

/* Slider */
.slider-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
}

.timeline-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: #3b82f6;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
}

/* Progress Track with Keyframe Markers */
.progress-track {
  position: relative;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: visible;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 4px;
  transition: width 0.1s linear;
}

.keyframe-marker {
  position: absolute;
  top: -4px;
  width: 8px;
  height: 16px;
  background: #f59e0b;
  border-radius: 2px;
  transform: translateX(-50%);
  cursor: pointer;
  transition: all 0.2s;
}

.keyframe-marker:hover {
  background: #d97706;
  transform: translateX(-50%) scale(1.2);
}

.keyframe-marker.auto {
  background: #8b5cf6;
}

.keyframe-marker.current {
  background: #10b981;
  box-shadow: 0 0 0 2px white, 0 0 0 4px #10b981;
}

/* Secondary Controls */
.secondary-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-group label {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
}

/* Dropdowns */
.speed-dropdown,
.keyframe-dropdown {
  position: relative;
}

.dropdown-toggle {
  padding: 4px 10px;
  border: 1px solid #cbd5e1;
  background: white;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  min-width: 100px;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  text-align: left;
  font-size: 12px;
  cursor: pointer;
}

.dropdown-item:hover {
  background: #f1f5f9;
}

.dropdown-item.active {
  background: #eff6ff;
  color: #3b82f6;
}

.dropdown-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 4px 0;
}

.toggle-buttons {
  display: flex;
  gap: 4px;
}

.toggle-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #cbd5e1;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  opacity: 0.5;
}

.toggle-btn.active {
  opacity: 1;
  background: #eff6ff;
  border-color: #3b82f6;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #cbd5e1;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

/* Info Panels */
.info-panels {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-panel {
  padding: 10px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.info-panel h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.keyframe-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kf-label {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.kf-meta {
  font-size: 11px;
  color: #64748b;
}

.kf-time {
  font-size: 10px;
  color: #94a3b8;
}

.ghost-list,
.prediction-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.ghost-badge {
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 11px;
  color: #475569;
}

.prediction-badge {
  padding: 2px 8px;
  background: #fef3c7;
  border-radius: 4px;
  font-size: 11px;
  color: #92400e;
}

.prediction-badge.high {
  background: #d1fae5;
  color: #065f46;
}

.prediction-badge.medium {
  background: #fef3c7;
  color: #92400e;
}

.more-badge {
  font-size: 11px;
  color: #64748b;
  padding: 2px 4px;
}

/* Keyframe Strip */
.keyframe-strip {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  overflow-x: auto;
  padding: 8px 0;
}

.keyframe-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 16px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.keyframe-chip:hover {
  background: #f1f5f9;
}

.keyframe-chip.current {
  background: #eff6ff;
  border-color: #3b82f6;
}

.keyframe-chip.auto {
  border-style: dashed;
}

.kf-icon {
  font-size: 10px;
}

.kf-name {
  color: #475569;
}
</style>
