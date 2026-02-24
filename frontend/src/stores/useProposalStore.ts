import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { 
  ProposalPayload, 
  ProposalStatus,
  CopilotRouteResponse,
  CopilotContext 
} from '@/types';

export function useProposalStore() {
  return defineStore('proposals', () => {
    // State
    const proposals = ref<ProposalPayload[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Getters
    const draftProposals = computed(() => proposals.value.filter(p => p.status === 'draft'));
    const appliedProposals = computed(() => proposals.value.filter(p => p.status === 'applied'));
    const proposalCount = computed(() => proposals.value.length);

    // Actions
    async function loadProposals(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const list = await apiGet<ProposalPayload[]>('/api/command/proposals');
        proposals.value = list;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load proposals';
      } finally {
        loading.value = false;
      }
    }

    async function applyProposal(proposalId: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        await apiPost(`/api/command/proposals/${proposalId}/apply`, {});
        // Update local state
        const proposal = proposals.value.find(p => p.proposal_id === proposalId);
        if (proposal) {
          proposal.status = 'applied';
          proposal.updated_at = new Date().toISOString();
        }
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to apply proposal';
        return false;
      } finally {
        loading.value = false;
      }
    }

    async function rejectProposal(proposalId: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        await apiPost(`/api/command/proposals/${proposalId}/reject`, {});
        const proposal = proposals.value.find(p => p.proposal_id === proposalId);
        if (proposal) {
          proposal.status = 'rejected';
          proposal.updated_at = new Date().toISOString();
        }
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to reject proposal';
        return false;
      } finally {
        loading.value = false;
      }
    }

    async function rollbackProposal(proposalId: string): Promise<boolean> {
      loading.value = true;
      error.value = null;
      try {
        await apiPost(`/api/command/proposals/${proposalId}/rollback`, {});
        const proposal = proposals.value.find(p => p.proposal_id === proposalId);
        if (proposal) {
          proposal.status = 'rolled_back';
          proposal.updated_at = new Date().toISOString();
        }
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to rollback proposal';
        return false;
      } finally {
        loading.value = false;
      }
    }

    function updateProposalStatus(proposalId: string, status: ProposalStatus): void {
      const proposal = proposals.value.find(p => p.proposal_id === proposalId);
      if (proposal) {
        proposal.status = status;
        proposal.updated_at = new Date().toISOString();
      }
    }

    function clear(): void {
      proposals.value = [];
      error.value = null;
    }

    return {
      proposals,
      loading,
      error,
      draftProposals,
      appliedProposals,
      proposalCount,
      loadProposals,
      applyProposal,
      rejectProposal,
      rollbackProposal,
      updateProposalStatus,
      clear,
    };
  })();
}
