<script setup lang="ts">
import { computed } from 'vue';
import { useGraphStore, useStudioStore, useOntologyStore } from '@/stores';
import GraphVisualizer from '@/components/GraphVisualizer.vue';

const graphStore = useGraphStore();
const studioStore = useStudioStore();
const ontologyStore = useOntologyStore();

const objectTypes = computed(() => ontologyStore.objectTypes);
const graphNodes = computed(() => graphStore.graphNodes);
const graphEdges = computed(() => graphStore.graphEdges);

const handleNodeCreate = async (payload: { node_id: string; label: string }) => {
  await graphStore.createNode(payload);
};

const handleNodeRename = async (payload: { node_id: string; label: string }) => {
  await graphStore.renameNode(payload);
};

const handleNodeDelete = async (payload: { node_id: string }) => {
  await graphStore.deleteNode(payload);
};

const handleEdgeCreate = async (payload: { source_id: string; target_id: string; label: string }) => {
  await graphStore.createEdge(payload);
};

const handleEdgeDelete = async (payload: { source_id: string; target_id: string; label: string }) => {
  await graphStore.deleteEdge(payload);
};
</script>

<template>
  <div class="home-view">
    <GraphVisualizer
      :object-types="objectTypes"
      :graph-nodes="graphNodes"
      :graph-edges="graphEdges"
      @node-create="handleNodeCreate"
      @node-rename="handleNodeRename"
      @node-delete="handleNodeDelete"
      @edge-create="handleEdgeCreate"
      @edge-delete="handleEdgeDelete"
    />
  </div>
</template>

<style scoped>
.home-view {
  height: 100%;
  width: 100%;
}
</style>
