import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiGet, apiPost } from '@/api/client';
import type { GraphSnapshotPayload, GraphNodePayload, GraphEdgePayload } from '@/types';

export function useGraphStore() {
  return defineStore('graph', () => {
    // State
    const graphNodes = ref<GraphNodePayload[]>([]);
    const graphEdges = ref<GraphEdgePayload[]>([]);
    const selectedNodeId = ref<string>('');
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Actions
    async function loadGraphSnapshot(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const payload = await apiGet<GraphSnapshotPayload>('/api/query/graph');
        graphNodes.value = payload.nodes;
        graphEdges.value = payload.edges;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load graph';
      } finally {
        loading.value = false;
      }
    }

    async function createNode(payload: { node_id: string; label: string }): Promise<boolean> {
      try {
        await apiPost('/api/command/graph/node/upsert', payload);
        graphNodes.value.unshift({
          node_id: payload.node_id,
          label: payload.label,
        });
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to create node';
        return false;
      }
    }

    async function renameNode(payload: { node_id: string; label: string }): Promise<boolean> {
      try {
        await apiPost('/api/command/graph/node/upsert', payload);
        const node = graphNodes.value.find(n => n.node_id === payload.node_id);
        if (node) {
          node.label = payload.label;
        }
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to rename node';
        return false;
      }
    }

    async function deleteNode(payload: { node_id: string }): Promise<boolean> {
      try {
        await apiPost('/api/command/graph/node/delete', payload);
        graphNodes.value = graphNodes.value.filter(n => n.node_id !== payload.node_id);
        graphEdges.value = graphEdges.value.filter(
          e => e.source_id !== payload.node_id && e.target_id !== payload.node_id
        );
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to delete node';
        return false;
      }
    }

    async function createEdge(payload: { source_id: string; target_id: string; label: string }): Promise<boolean> {
      try {
        await apiPost('/api/command/graph/edge/upsert', payload);
        graphEdges.value.unshift({
          edge_id: `edge-${Date.now()}`,
          source_id: payload.source_id,
          target_id: payload.target_id,
          label: payload.label,
        });
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to create edge';
        return false;
      }
    }

    async function deleteEdge(payload: { source_id: string; target_id: string; label: string }): Promise<boolean> {
      try {
        await apiPost('/api/command/graph/edge/delete', payload);
        graphEdges.value = graphEdges.value.filter(
          e => !(e.source_id === payload.source_id && 
                e.target_id === payload.target_id && 
                e.label === payload.label)
        );
        return true;
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to delete edge';
        return false;
      }
    }

    function selectNode(nodeId: string): void {
      selectedNodeId.value = nodeId;
    }

    function clear(): void {
      graphNodes.value = [];
      graphEdges.value = [];
      selectedNodeId.value = '';
      error.value = null;
    }

    return {
      graphNodes,
      graphEdges,
      selectedNodeId,
      loading,
      error,
      loadGraphSnapshot,
      createNode,
      renameNode,
      deleteNode,
      createEdge,
      deleteEdge,
      selectNode,
      clear,
    };
  })();
}
