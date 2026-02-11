<script setup lang="ts">
type ProposalStatus = "draft" | "applied" | "rejected" | "rolled_back";

type Proposal = {
  proposal_id: string;
  title: string;
  intent: string;
  status: ProposalStatus;
  created_at: string;
  updated_at: string;
};

const props = defineProps<{
  proposal: Proposal;
  busy: boolean;
}>();

const emit = defineEmits<{
  (event: "apply", proposalId: string): void;
  (event: "reject", proposalId: string): void;
  (event: "rollback", proposalId: string): void;
}>();

const applyProposal = () => emit("apply", props.proposal.proposal_id);
const rejectProposal = () => emit("reject", props.proposal.proposal_id);
const rollbackProposal = () => emit("rollback", props.proposal.proposal_id);

const statusLabel: Record<ProposalStatus, string> = {
  draft: "草稿",
  applied: "已应用",
  rejected: "已拒绝",
  rolled_back: "已回滚",
};
</script>

<template>
  <article class="proposal-card">
    <header class="proposal-header">
      <h3>{{ proposal.title }}</h3>
      <span class="status">{{ statusLabel[proposal.status] }}</span>
    </header>
    <p class="intent">{{ proposal.intent }}</p>
    <div class="meta">
      <span>编号: {{ proposal.proposal_id }}</span>
      <span>更新时间: {{ proposal.updated_at }}</span>
    </div>
    <footer class="actions">
      <button type="button" @click="applyProposal" :disabled="busy">应用</button>
      <button type="button" @click="rejectProposal" :disabled="busy">拒绝</button>
      <button type="button" @click="rollbackProposal" :disabled="busy">回滚</button>
    </footer>
  </article>
</template>

<style scoped>
.proposal-card {
  border: 1px solid #ccd9e3;
  border-radius: 10px;
  padding: 14px;
  background: #ffffff;
  display: grid;
  gap: 10px;
}

.proposal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.proposal-header h3 {
  margin: 0;
  font-size: 16px;
  color: #0f2f41;
}

.status {
  text-transform: uppercase;
  font-size: 12px;
  color: #0d6c8d;
  font-weight: 700;
}

.intent {
  margin: 0;
  color: #2f4858;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #5d7280;
}

.actions {
  display: flex;
  gap: 8px;
}

.actions button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
