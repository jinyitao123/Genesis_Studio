<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { useTimelineStore } from '@/stores/useTimelineStore';
import type { GhostFrame, Coordinate, GraphNodePayload, GraphEdgePayload } from '@/types';

const props = defineProps<{
  // Current entities to overlay ghosts onto
  currentNodes?: GraphNodePayload[];
  currentEdges?: GraphEdgePayload[];
  // Canvas dimensions for positioning
  width?: number;
  height?: number;
  // Whether to show entity labels
  showLabels?: boolean;
  // Whether to show entity types
  showTypes?: boolean;
  // Color scheme for ghosts
  ghostColor?: string;
  // Custom opacity multiplier
  opacityMultiplier?: number;
}>();

const emit = defineEmits<{
  (event: 'ghostClick', ghostFrame: GhostFrame, nodeId: string): void;
  (event: 'ghostHover', ghostFrame: GhostFrame | null, nodeId: string | null): void;
}>();

// Use timeline store
const timelineStore = useTimelineStore();

// Local state
const hoveredNodeId = ref<string | null>(null);

// Computed ghost frames from store
const ghostFrames = computed(() => timelineStore.currentGhostFrames);

// Filter ghost frames to show only relevant ones
const visibleGhostFrames = computed(() => {
  const frames = ghostFrames.value;
  
  // Show maximum of 5 ghost frames to avoid visual clutter
  if (frames.length <= 5) return frames;
  
  // Show evenly distributed ghosts
  const step = Math.ceil(frames.length / 5);
  return frames.filter((_, index) => index % step === 0);
});

// Style for ghost nodes
const getGhostNodeStyle = (frame: GhostFrame, node: GraphNodePayload) => {
  const opacity = (frame.opacity ?? 0.3) * (props.opacityMultiplier ?? 1);
  
  return {
    opacity: Math.max(0.1, Math.min(1, opacity)),
    fill: props.ghostColor || '#94a3b8',
    stroke: props.ghostColor || '#64748b',
    strokeWidth: 1,
    strokeDasharray: '4,2',
  };
};

// Style for ghost edges
const getGhostEdgeStyle = (frame: GhostFrame) => {
  const opacity = (frame.opacity ?? 0.3) * (props.opacityMultiplier ?? 1);
  
  return {
    opacity: Math.max(0.1, Math.min(1, opacity)),
    stroke: props.ghostColor || '#94a3b8',
    strokeWidth: 1,
    strokeDasharray: '4,2',
  };
};

// Get position from ghost frame or infer from properties
const getGhostPosition = (
  frame: GhostFrame,
  node: GraphNodePayload
): Coordinate | undefined => {
  // Priority: explicit position > inferred from properties
  if (frame.position) {
    return frame.position;
  }
  
  // Try to extract position from properties
  if (frame.properties) {
    const x = frame.properties.x as number | undefined;
    const y = frame.properties.y as number | undefined;
    if (x !== undefined && y !== undefined) {
      return { x, y, z: frame.properties.z as number | undefined };
    }
  }
  
  // Fall back to current node position
  const currentNode = props.currentNodes?.find(n => n.node_id === node.node_id);
  if (currentNode?.properties) {
    const x = currentNode.properties.x as number | undefined;
    const y = currentNode.properties.y as number | undefined;
    if (x !== undefined && y !== undefined) {
      return { x, y };
    }
  }
  
  return undefined;
};

// Calculate ghost trail (path of movement)
const ghostTrail = computed(() => {
  const frames = visibleGhostFrames.value;
  if (frames.length < 2) return [];
  
  const trails: Map<string, Array<{ frame: GhostFrame; position: Coordinate }>> = new Map();
  
  for (const frame of frames) {
    if (!frame.position) continue;
    
    // Create unique key based on tick
    const key = `ghost_${frame.tick}`;
    if (!trails.has(key)) {
      trails.set(key, []);
    }
    trails.get(key)!.push({ frame, position: frame.position });
  }
  
  return trails;
});

// Handle node hover
const onNodeHover = (frame: GhostFrame, nodeId: string | null) => {
  hoveredNodeId.value = nodeId;
  emit('ghostHover', nodeId ? frame : null, nodeId);
};

// Handle node click
const onNodeClick = (frame: GhostFrame, nodeId: string) => {
  emit('ghostClick', frame, nodeId);
};

// Format tick for display
const formatTick = (tick: number): string => {
  return `T${tick}`;
};

// Lifecycle - watch for changes
watch(() => ghostFrames.value.length, () => {
  // Trigger recalculation when ghost frames change
});

watch(() => timelineStore.currentTick, () => {
  // Current tick changed, ghost frames will update automatically via computed
});
</script>

<template>
  <g class="ghost-overlay">
    <!-- Ghost Edges -->
    <g class="ghost-edges">
      <template v-for="frame in visibleGhostFrames" :key="`edges-${frame.tick}`">
        <line
          v-for="edge in currentEdges"
          :key="`ghost-edge-${frame.tick}-${edge.edge_id}`"
          class="ghost-edge"
          :class="{ interactive: hoveredNodeId !== null }"
          :x1="0"
          :y1="0"
          :x2="0"
          :y2="0"
          :style="getGhostEdgeStyle(frame)"
          :data-frame-tick="frame.tick"
          :data-edge-id="edge.edge_id"
        />
        <!-- Note: Actual positioning would be handled by parent graph component -->
      </template>
    </g>

    <!-- Ghost Nodes -->
    <g class="ghost-nodes">
      <template v-for="frame in visibleGhostFrames" :key="`nodes-${frame.tick}`">
        <g
          v-for="node in currentNodes"
          :key="`ghost-node-${frame.tick}-${node.node_id}`"
          class="ghost-node-group"
          :class="{ interactive: hoveredNodeId !== null }"
          :transform="getGhostPosition(frame, node) ? `translate(${getGhostPosition(frame, node)!.x}, ${getGhostPosition(frame, node)!.y})` : ''"
          @mouseenter="onNodeHover(frame, node.node_id)"
          @mouseleave="onNodeHover(frame, null)"
          @click="onNodeClick(frame, node.node_id)"
        >
          <!-- Ghost node circle -->
          <circle
            r="20"
            class="ghost-node"
            :style="getGhostNodeStyle(frame, node)"
          />
          
          <!-- Ghost node label -->
          <text
            v-if="showLabels"
            y="35"
            class="ghost-node-label"
            :fill="ghostColor || '#64748b'"
            :opacity="(frame.opacity ?? 0.3) * (opacityMultiplier ?? 1)"
          >
            {{ node.label }}
          </text>
          
          <!-- Ghost node type badge -->
          <text
            v-if="showTypes"
            y="-25"
            class="ghost-node-type"
            :fill="ghostColor || '#64748b'"
            :opacity="(frame.opacity ?? 0.3) * (opacityMultiplier ?? 1)"
          >
            {{ formatTick(frame.tick) }}
          </text>
        </g>
      </template>
    </g>

    <!-- Ghost Trail Lines (connecting ghost positions) -->
    <g class="ghost-trails">
      <template v-for="[trailId, trailPoints] in ghostTrail" :key="`trail-${trailId}`">
        <polyline
          v-if="trailPoints.length >= 2"
          :points="trailPoints.map(p => `${p.position.x},${p.position.y}`).join(' ')"
          class="ghost-trail"
          :stroke="ghostColor || '#94a3b8'"
          :stroke-width="1"
          :stroke-dasharray="'4,2'"
          :opacity="0.5 * (opacityMultiplier ?? 1)"
          fill="none"
        />
      </template>
    </g>

    <!-- Hover Info Tooltip -->
    <g 
      v-if="hoveredNodeId" 
      class="ghost-tooltip"
      :transform="`translate(${width || 0 - 120}, 20)`"
    >
      <rect
        x="0"
        y="0"
        width="110"
        height="auto"
        rx="6"
        fill="white"
        stroke="#e2e8f0"
        stroke-width="1"
        filter="drop-shadow(0 2px 4px rgba(0,0,0,0.1))"
      />
      
      <text
        v-for="(value, key) in visibleGhostFrames[0]?.properties"
        :key="key"
        :y="20 + (Object.keys(value).indexOf(key) * 18)"
        x="10"
        class="ghost-tooltip-text"
        fill="#475569"
      >
        {{ key }}: {{ String(value).substring(0, 15) }}{{ String(value).length > 15 ? '...' : '' }}
      </text>
      
      <text
        x="10"
        y="16"
        class="ghost-tooltip-title"
        fill="#1e293b"
        font-weight="600"
      >
        Ghost Frame
      </text>
    </g>
  </g>
</template>

<style scoped>
.ghost-overlay {
  pointer-events: none;
}

.ghost-overlay .ghost-node {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.ghost-overlay .ghost-node-group.interactive {
  pointer-events: all;
  cursor: pointer;
}

.ghost-overlay .ghost-node-group.interactive:hover .ghost-node {
  stroke-width: 2;
  stroke-dasharray: none;
}

.ghost-overlay .ghost-edge {
  transition: opacity 0.2s ease;
}

.ghost-overlay .ghost-edge.interactive {
  pointer-events: all;
  cursor: pointer;
}

.ghost-overlay .ghost-trail {
  transition: opacity 0.2s ease;
}

.ghost-overlay .ghost-node-label {
  font-size: 11px;
  text-anchor: middle;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.ghost-overlay .ghost-node-type {
  font-size: 10px;
  text-anchor: middle;
  font-weight: 500;
}

.ghost-overlay .ghost-tooltip {
  pointer-events: none;
}

.ghost-tooltip-text {
  font-size: 11px;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.ghost-tooltip-title {
  font-size: 12px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Animation for ghost appearance */
@keyframes ghostAppear {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.ghost-node-group {
  animation: ghostAppear 0.3s ease-out;
}

/* Smooth fade for ghost trail */
.ghost-trail {
  transition: stroke-dashoffset 0.5s ease;
}
</style>
