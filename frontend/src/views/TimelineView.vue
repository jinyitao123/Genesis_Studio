<script setup lang="ts">
import { useStudioStore, useEventStore } from '@/stores';
import TimelineController from '@/components/TimelineController.vue';

const studioStore = useStudioStore();
const eventStore = useEventStore();

const selectedTick = computed({
  get: () => studioStore.selectedTick,
  set: (val: number) => studioStore.setSelectedTick(val),
});

const latestEvents = computed(() => eventStore.latestEvents);
</script>

<template>
  <div class="timeline-view">
    <TimelineController v-model="selectedTick" :events="latestEvents" />
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'TimelineView'
};
</script>

<style scoped>
.timeline-view {
  height: 100%;
  width: 100%;
}
</style>
