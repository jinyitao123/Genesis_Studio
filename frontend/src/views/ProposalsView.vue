<script setup lang="ts">
import { useProposalStore, useCopilotStore, useStudioStore } from '@/stores';
import ProposalCard from '@/components/ProposalCard.vue';

const proposalStore = useProposalStore();
const copilotStore = useCopilotStore();
const studioStore = useStudioStore();

const proposals = computed(() => proposalStore.proposals);
const busy = computed(() => proposalStore.loading || copilotStore.loading || studioStore.busy);

const handleApplyProposal = async (proposalId: string) => {
  await proposalStore.applyProposal(proposalId);
};

const handleRejectProposal = async (proposalId: string) => {
  await proposalStore.rejectProposal(proposalId);
};

const performProposalAction = async (proposalId: string, action: "apply" | "reject" | "rollback") => {
  if (action === 'apply') {
    await proposalStore.applyProposal(proposalId);
  } else if (action === 'reject') {
    await proposalStore.rejectProposal(proposalId);
  }
};
</script>

<template>
  <div class="proposals-view proposals-grid">
    <ProposalCard
      v-for="proposal in proposals"
      :key="proposal.proposal_id"
      :proposal="proposal"
      :busy="busy"
      @apply="(id) => performProposalAction(id, 'apply')"
      @reject="(id) => performProposalAction(id, 'reject')"
      @rollback="(id) => performProposalAction(id, 'rollback')"
    />
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'ProposalsView'
};
</script>

<style scoped>
.proposals-view {
  height: 100%;
  width: 100%;
}

.proposals-grid {
  display: grid;
  gap: 10px;
}
</style>
