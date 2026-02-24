<script setup lang="ts">
import { ref, computed } from 'vue';
import { useOntologyStore } from '@/stores';
import type { ObjectTypeDefinition } from '@/types';

interface TreeNode {
  id: string;
  label: string;
  type_uri: string;
  children: TreeNode[];
  depth: number;
}

const props = defineProps<{
  searchQuery?: string;
}>();

const emit = defineEmits<{
  (e: 'select', typeUri: string): void;
}>();

const ontologyStore = useOntologyStore();
const objectTypes = computed(() => ontologyStore.objectTypes);
const selectedTypeUri = ref<string | null>(null);
const expandedNodes = ref<Set<string>>(new Set());

function buildTree(types: ObjectTypeDefinition[]): TreeNode[] {
  const nodeMap = new Map<string, TreeNode>();
  const rootNodes: TreeNode[] = [];
  
  types.forEach(type => {
    nodeMap.set(type.type_uri, {
      id: type.type_uri,
      label: type.display_name,
      type_uri: type.type_uri,
      children: [],
      depth: 0,
    });
  });
  
  types.forEach(type => {
    const node = nodeMap.get(type.type_uri)!;
    if (type.parent_type && nodeMap.has(type.parent_type)) {
      const parent = nodeMap.get(type.parent_type)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      rootNodes.push(node);
    }
  });
  
  return rootNodes;
}

function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  if (!query.trim()) return nodes;
  const lower = query.toLowerCase();
  
  function filter(node: TreeNode): TreeNode | null {
    const matches = node.label.toLowerCase().includes(lower) || node.type_uri.toLowerCase().includes(lower);
    const filteredChildren = node.children.map(c => filter(c)).filter((c): c is TreeNode => c !== null);
    if (matches || filteredChildren.length > 0) {
      return { ...node, children: filteredChildren };
    }
    return null;
  }
  
  return nodes.map(n => filter(n)).filter((n): n is TreeNode => n !== null);
}

const tree = computed(() => filterTree(buildTree(objectTypes.value), props.searchQuery || ''));

function getIcon(typeUri: string): string {
  if (typeUri.includes('unit')) return '🎖️';
  if (typeUri.includes('building')) return '🏢';
  if (typeUri.includes('vehicle')) return '🚗';
  if (typeUri.includes('item')) return '📦';
  if (typeUri.includes('terrain')) return '🌍';
  if (typeUri.includes('action')) return '⚡';
  if (typeUri.includes('link')) return '🔗';
  return '📁';
}

function toggle(id: string) {
  if (expandedNodes.value.has(id)) expandedNodes.value.delete(id);
  else expandedNodes.value.add(id);
}

function select(node: TreeNode) {
  selectedTypeUri.value = node.id;
  emit('select', node.id);
}

function isExpanded(id: string): boolean {
  return expandedNodes.value.has(id);
}

function isSelected(id: string): boolean {
  return selectedTypeUri.value === id;
}

function expandAll() {
  function traverse(nodes: TreeNode[]) {
    nodes.forEach(n => { expandedNodes.value.add(n.id); traverse(n.children); });
  }
  traverse(tree.value);
}

function collapseAll() {
  expandedNodes.value.clear();
}
</script>

<template>
  <div class="ontology-explorer">
    <div class="explorer-toolbar">
      <button class="toolbar-btn" @click="expandAll" title="展开全部">📖</button>
      <button class="toolbar-btn" @click="collapseAll" title="折叠全部">📕</button>
    </div>
    <div class="tree-container">
      <ul class="tree-list">
        <template v-for="node in tree" :key="node.id">
          <TreeNodeItem
            :node="node"
            :expanded="isExpanded(node.id)"
            :selected="isSelected(node.id)"
            :icon="getIcon(node.type_uri)"
            @toggle="toggle(node.id)"
            @select="select"
          />
        </template>
        <li v-if="tree.length === 0" class="no-results">未找到类型</li>
      </ul>
    </div>
    <div class="explorer-footer">{{ objectTypes.length }} 个类型</div>
  </div>
</template>

<style scoped>
.ontology-explorer { height: 100%; display: flex; flex-direction: column; }
.explorer-toolbar { display: flex; gap: 4px; padding: 8px; border-bottom: 1px solid #e5e7eb; }
.toolbar-btn { padding: 4px 8px; border: 1px solid #e5e7eb; background: #f9fafb; border-radius: 4px; cursor: pointer; font-size: 12px; }
.toolbar-btn:hover { background: #f3f4f6; border-color: #d1d5db; }
.tree-container { flex: 1; overflow-y: auto; padding: 8px; }
.tree-list { list-style: none; margin: 0; padding: 0; }
.no-results { padding: 16px; text-align: center; color: #9ca3af; font-size: 13px; }
.explorer-footer { padding: 8px; border-top: 1px solid #e5e7eb; background: #f9fafb; font-size: 11px; color: #6b7280; }
</style>
