<script setup lang="ts">
import { useCopilotStore, useGraphStore, useOntologyStore, useEventStore, useStudioStore } from '@/stores';
import CopilotChat from '@/components/CopilotChat.vue';

const copilotStore = useCopilotStore();
const graphStore = useGraphStore();
const ontologyStore = useOntologyStore();
const eventStore = useEventStore();
const studioStore = useStudioStore();

const busy = computed(() => copilotStore.loading || studioStore.busy);

const copilotContext = computed(() => ({
  selectedNodes: graphStore.selectedNodeId ? [graphStore.selectedNodeId] : [],
  currentView: studioStore.activeTab,
  objectTypes: ontologyStore.objectTypes.map(ot => ot.type_uri),
  recentEvents: eventStore.latestEvents.slice(-10).map(e => e.action_id),
  tick: studioStore.selectedTick,
}));

const handleCopilotMessage = async (payload: { intent: string; prompt: string; context: Record<string, unknown> }) => {
  await copilotStore.runCopilot(payload.intent, payload.prompt, payload.context as any);
};

const handleApplyProposal = async (proposalId: string) => {
  // Handle proposal application
};

const handleRejectProposal = async (proposalId: string) => {
  // Handle proposal rejection
};
</script>

<template>
  <div class="copilot-view">
    <CopilotChat
      :context="copilotContext"
      :busy="busy"
      @send-message="handleCopilotMessage"
      @apply-proposal="handleApplyProposal"
      @reject-proposal="handleRejectProposal"
    />
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'CopilotView'
};
</script>

<style scoped>
.copilot-view {
  height: 100%;
  width: 100%;
}
</style>
