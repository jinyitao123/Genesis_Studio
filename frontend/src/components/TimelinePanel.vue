<script setup lang="ts">
import { computed, ref } from "vue";

type EventPayload = {
  event_id: string;
  action_id: string;
  created_at: string;
  source_id?: string | null;
  target_id?: string | null;
};

const props = defineProps<{
  events: EventPayload[];
}>();

const emit = defineEmits<{
  (event: "event-select", payload: EventPayload): void;
  (event: "event-hover", payload: EventPayload | null): void;
}>();

const zoomLevel = ref<number>(1);
const panOffset = ref<number>(0);
const filterText = ref<string>("");
const selectedEventId = ref<string>("");
const viewMode = ref<"list" | "timeline">("timeline");

const filteredEvents = computed(() => {
  if (!filterText.value.trim()) return props.events;
  const needle = filterText.value.toLowerCase();
  return props.events.filter(
    (e) =>
      e.action_id.toLowerCase().includes(needle) ||
      e.event_id.toLowerCase().includes(needle) ||
      (e.source_id && e.source_id.toLowerCase().includes(needle)) ||
      (e.target_id && e.target_id.toLowerCase().includes(needle))
  );
});

const visibleEvents = computed(() => {
  const start = Math.max(0, Math.floor(panOffset.value));
  const count = Math.floor(50 * zoomLevel.value);
  return filteredEvents.value.slice(start, start + count);
});

const totalDuration = computed(() => {
  if (props.events.length < 2) return 0;
  const first = new Date(props.events[0].created_at).getTime();
  const last = new Date(props.events[props.events.length - 1].created_at).getTime();
  return last - first;
});

const formatTime = (ts: string) => {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
};

const selectEvent = (evt: EventPayload) => {
  selectedEventId.value = evt.event_id;
  emit("event-select", evt);
};

const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value * 1.2, 5);
};

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value / 1.2, 0.2);
};

const panLeft = () => {
  panOffset.value = Math.max(0, panOffset.value - 10 * zoomLevel.value);
};

const panRight = () => {
  const maxOffset = Math.max(0, filteredEvents.value.length - 50 * zoomLevel.value);
  panOffset.value = Math.min(maxOffset, panOffset.value + 10 * zoomLevel.value);
};
</script>

<template>
  <section class="panel-section">
    <header class="timeline-header">
      <h3>时间线控制器</h3>
      <div class="stats">
        <span>事件: {{ filteredEvents.length }}</span>
        <span v-if="totalDuration > 0">跨度: {{ (totalDuration / 1000).toFixed(1) }}s</span>
      </div>
    </header>

    <div class="toolbar">
      <input v-model="filterText" type="text" placeholder="过滤事件..." class="filter-input" />
      <div class="view-toggle">
        <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">列表</button>
        <button :class="{ active: viewMode === 'timeline' }" @click="viewMode = 'timeline'">时间轴</button>
      </div>
    </div>

    <div class="zoom-controls">
      <button @click="zoomOut">-</button>
      <span>缩放: {{ (zoomLevel * 100).toFixed(0) }}%</span>
      <button @click="zoomIn">+</button>
      <button @click="panLeft">←</button>
      <button @click="panRight">→</button>
      <span>偏移: {{ Math.floor(panOffset) }}</span>
    </div>

    <div v-if="viewMode === 'list'" class="event-list">
      <div
        v-for="item in visibleEvents"
        :key="item.event_id"
        :class="['event-item', { selected: selectedEventId === item.event_id }]"
        @click="selectEvent(item)"
        @mouseenter="emit('event-hover', item)"
        @mouseleave="emit('event-hover', null)"
      >
        <span class="event-time">{{ formatTime(item.created_at) }}</span>
        <span class="event-action">{{ item.action_id }}</span>
        <span class="event-id">{{ item.event_id }}</span>
      </div>
    </div>

    <div v-else class="timeline-view">
      <div
        v-for="(item, index) in visibleEvents"
        :key="item.event_id"
        :class="['timeline-item', { selected: selectedEventId === item.event_id }]"
        :style="{ left: `${(index * 100) / visibleEvents.length}%` }"
        @click="selectEvent(item)"
        @mouseenter="emit('event-hover', item)"
        @mouseleave="emit('event-hover', null)"
      >
        <div class="timeline-dot"></div>
        <div class="timeline-label">{{ item.action_id }}</div>
      </div>
    </div>

    <div class="range-info">
      <span>显示: {{ Math.floor(panOffset) }} - {{ Math.floor(panOffset + visibleEvents.length) }}</span>
    </div>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-header h3 {
  margin: 0;
}

.stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #5d7280;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #c5d9e4;
  border-radius: 8px;
  font-size: 13px;
}

.view-toggle {
  display: flex;
  gap: 4px;
}

.view-toggle button {
  padding: 6px 12px;
  border: 1px solid #9ec0d2;
  background: #f4fafc;
  border-radius: 6px;
  cursor: pointer;
}

.view-toggle button.active {
  background: #0d6c8d;
  color: white;
  border-color: #0d6c8d;
}

.zoom-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.zoom-controls button {
  width: 28px;
  height: 28px;
  border: 1px solid #9ec0d2;
  background: #f4fafc;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.event-list {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  max-height: 200px;
  overflow-y: auto;
  background: #f8fbfd;
}

.event-item {
  display: grid;
  grid-template-columns: 80px 1fr 120px;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #e8f1f5;
  cursor: pointer;
  font-size: 13px;
  align-items: center;
}

.event-item:hover {
  background: #e9f4fa;
}

.event-item.selected {
  background: #d4edfc;
}

.event-time {
  color: #5d7280;
  font-family: monospace;
}

.event-action {
  font-weight: 500;
  color: #1e495f;
}

.event-id {
  color: #8ba3b3;
  font-size: 11px;
  text-align: right;
}

.timeline-view {
  position: relative;
  height: 80px;
  border: 1px solid #cde0e8;
  border-radius: 10px;
  background: linear-gradient(to bottom, #f8fbfd, #eef6fa);
  overflow: hidden;
}

.timeline-item {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.timeline-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #0d6c8d;
  border: 2px solid white;
  box-shadow: 0 0 0 1px #0d6c8d;
}

.timeline-item.selected .timeline-dot {
  background: #e74c3c;
  box-shadow: 0 0 0 2px #e74c3c;
}

.timeline-label {
  font-size: 10px;
  color: #5d7280;
  white-space: nowrap;
  transform: rotate(-45deg);
  transform-origin: center;
}

.range-info {
  font-size: 12px;
  color: #8ba3b3;
  text-align: right;
}
</style>
