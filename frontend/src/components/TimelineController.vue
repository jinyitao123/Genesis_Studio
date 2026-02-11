<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type EventPayload = {
  event_id: string;
  action_id: string;
  created_at: string;
};

const props = defineProps<{
  modelValue: number;
  events: EventPayload[];
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: number): void;
}>();

const isPlaying = ref<boolean>(false);
const fineMode = ref<boolean>(false);
let playTimer: ReturnType<typeof setInterval> | null = null;

const bufferedEvents = computed(() => props.events.slice(-1000));
const maxTick = computed(() => Math.max(bufferedEvents.value.length - 1, 0));
const keyframes = computed(() =>
  bufferedEvents.value
    .map((item, index) => ({
      id: item.event_id,
      tick: index,
      action: item.action_id,
    }))
    .filter((_, index) => index % 3 === 0)
    .slice(-10),
);

const updateTick = (value: number) => {
  emit("update:modelValue", Math.min(Math.max(value, 0), maxTick.value));
};

const stopPlay = () => {
  if (playTimer !== null) {
    clearInterval(playTimer);
    playTimer = null;
  }
  isPlaying.value = false;
};

const togglePlay = () => {
  if (isPlaying.value) {
    stopPlay();
    return;
  }
  isPlaying.value = true;
  playTimer = setInterval(() => {
    if (maxTick.value === 0) {
      stopPlay();
      return;
    }
    const next = props.modelValue >= maxTick.value ? 0 : props.modelValue + 1;
    updateTick(next);
  }, 450);
};

const stepTick = (direction: 1 | -1) => {
  const delta = fineMode.value ? 1 : 5;
  updateTick(props.modelValue + direction * delta);
};

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === "Shift") {
    fineMode.value = true;
  }
};

const onKeyUp = (event: KeyboardEvent) => {
  if (event.key === "Shift") {
    fineMode.value = false;
  }
};

onMounted(() => {
  window.addEventListener("keydown", onKeyDown);
  window.addEventListener("keyup", onKeyUp);
});

onBeforeUnmount(() => {
  stopPlay();
  window.removeEventListener("keydown", onKeyDown);
  window.removeEventListener("keyup", onKeyUp);
});
</script>

<template>
  <section class="panel-section">
    <header class="timeline-header">
      <h3>时间线控制器</h3>
      <span class="mode">{{ fineMode ? "精细模式" : "快速模式" }}</span>
    </header>

    <div class="controls">
      <button type="button" @click="stepTick(-1)">◁◁</button>
      <button type="button" @click="togglePlay">{{ isPlaying ? "暂停" : "播放" }}</button>
      <button type="button" @click="stepTick(1)">▷▷</button>
      <span>帧 {{ modelValue + 1 }} / {{ maxTick + 1 }}</span>
    </div>

    <input
      type="range"
      :min="0"
      :max="maxTick"
      :value="modelValue"
      @input="updateTick(Number(($event.target as HTMLInputElement).value))"
    />

    <div class="keyframe-strip" v-if="keyframes.length > 0">
      <button
        v-for="frame in keyframes"
        :key="frame.id"
        type="button"
        class="keyframe"
        @click="updateTick(frame.tick)"
      >
        K{{ frame.tick + 1 }} · {{ frame.action }}
      </button>
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

.mode {
  font-size: 12px;
  color: #2a657f;
  font-weight: 700;
}

.controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.controls button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.controls span {
  font-size: 13px;
  color: #375263;
}

.keyframe-strip {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.keyframe {
  border: 1px solid #c4d8e2;
  background: #fff;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  color: #264457;
  cursor: pointer;
}
</style>
