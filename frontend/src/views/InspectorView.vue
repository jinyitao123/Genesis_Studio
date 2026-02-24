<script setup lang="ts">
import { useStudioStore, useOntologyStore, useEventStore } from '@/stores';
import InspectorPanel from '@/components/InspectorPanel.vue';

const studioStore = useStudioStore();
const ontologyStore = useOntologyStore();
const eventStore = useEventStore();

const selectedTick = computed(() => studioStore.selectedTick);
const activeTab = computed(() => studioStore.activeTab);
const objectTypes = computed(() => ontologyStore.objectTypes);
const latestEvents = computed(() => eventStore.latestEvents);
const transactions = computed(() => eventStore.transactions);

const inspectorPayload = computed(() => ({
  tick: selectedTick.value,
  active_tab: activeTab.value,
  object_types_count: objectTypes.value.length,
  events_count: latestEvents.value.length,
  transactions_count: transactions.value.length,
}));
</script>

<template>
  <div class="inspector-view">
    <InspectorPanel :payload="inspectorPayload" />
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'InspectorView'
};
</script>

<style scoped>
.inspector-view {
  height: 100%;
  width: 100%;
}
</style>
