<script setup lang="ts">
interface Props {
  node: {
    id: string;
    label: string;
    children: any[];
    isLeaf: boolean;
    depth: number;
  };
  expanded: boolean;
  selected: boolean;
  depth: number;
  icon: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'toggle'): void;
  (e: 'select'): void;
  (e: 'click', event: MouseEvent): void;
}>();

const handleClick = (event: MouseEvent) => {
  emit('click', event);
};
</script>

<template>
  <li class="tree-item">
    <div 
      class="item-content"
      :class="{ 
        selected: selected,
        'has-children': !isLeaf
      }"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      @click="handleClick"
    >
      <button 
        class="expand-btn"
        :class="{ expanded: expanded }"
        @click.stop="emit('toggle')"
        @dblclick.stop="emit('toggle')"
      >
        <span v-if="!isLeaf">{{ expanded ? '▼' : '▶' }}</span>
        <span v-else class="leaf-spacer">•</span>
      </button>
      
      <span class="item-icon">{{ icon }}</span>
      <span class="item-label">{{ label }}</span>
    </div>
    
    <ul v-if="expanded && !isLeaf" class="children-list">
      <TreeItem
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :expanded="expanded"
        :selected="child._selected"
        :depth="child.depth"
        :icon="child._icon"
        @toggle="() => {}"
        @select="() => {}"
        @click="(e) => {}"
      />
    </ul>
  </li>
</template>

<script lang="ts">
import { computed } from 'vue';

interface TreeChildNode {
  id: string;
  label: string;
  children: TreeChildNode[];
  isLeaf: boolean;
  depth: number;
  _selected?: boolean;
  _expanded?: boolean;
  _icon?: string;
}

export default {
  name: 'TreeItem',
  props: {
    node: {
      type: Object as () => TreeChildNode,
      required: true,
    },
    expanded: {
      type: Boolean,
      default: false,
    },
    selected: {
      type: Boolean,
      default: false,
    },
    depth: {
      type: Number,
      default: 0,
    },
    icon: {
      type: String,
      default: '📁',
    },
  },
  emits: ['toggle', 'select', 'click'],
  setup(props: any, { emit }: any) {
    const isLeaf = computed(() => props.node.isLeaf);
    
    return {
      isLeaf,
      emit,
    };
  },
};
</script>

<style scoped>
.tree-item {
  margin: 2px 0;
}

.item-content {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.item-content:hover {
  background: #f3f4f6;
}

.item-content.selected {
  background: #dbeafe;
  color: #1e40af;
}

.expand-btn {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  font-size: 8px;
  color: #6b7280;
  cursor: pointer;
  flex-shrink: 0;
}

.expand-btn:hover {
  color: #374151;
}

.leaf-spacer {
  color: transparent;
}

.item-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.item-label {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.children-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
</style>
