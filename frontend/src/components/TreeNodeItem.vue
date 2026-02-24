<script setup lang="ts">
interface TreeNode {
  id: string;
  label: string;
  children: TreeNode[];
  depth: number;
}

const props = defineProps<{
  node: TreeNode;
  expanded: boolean;
  selected: boolean;
  icon: string;
}>();

const emit = defineEmits<{
  (e: 'toggle'): void;
  (e: 'select', node: TreeNode): void;
}>();

function handleClick() {
  if (props.node.children.length > 0) {
    emit('toggle');
  } else {
    emit('select', props.node);
  }
}
</script>

<template>
  <li class="tree-node">
    <div 
      class="node-content"
      :class="{ selected, 'has-children': node.children.length > 0 }"
      :style="{ paddingLeft: `${node.depth * 16 + 8}px` }"
      @click="handleClick"
    >
      <span class="expand-icon" :class="{ expanded: expanded }">
        {{ node.children.length > 0 ? (expanded ? '▼' : '▶') : '•' }}
      </span>
      <span class="node-icon">{{ icon }}</span>
      <span class="node-label">{{ label }}</span>
    </div>
    <ul v-if="expanded && node.children.length > 0" class="children">
      <TreeNodeItem
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :expanded="false"
        :selected="false"
        :icon="icon"
        @toggle="() => {}"
        @select="(n) => emit('select', n)"
      />
    </ul>
  </li>
</template>

<script lang="ts">
export default {
  name: 'TreeNodeItem'
};
</script>

<style scoped>
.tree-node { margin: 2px 0; }
.node-content {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.node-content:hover { background: #f3f4f6; }
.node-content.selected { background: #dbeafe; color: #1e40af; }
.expand-icon {
  width: 12px;
  font-size: 8px;
  color: #6b7280;
  text-align: center;
}
.expand-icon.expanded { color: #374151; }
.node-icon { font-size: 14px; }
.node-label { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.children { list-style: none; margin: 0; padding: 0; }
</style>
