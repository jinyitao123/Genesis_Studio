<script setup lang="ts">
import { computed, ref } from "vue";

type LogicNode = {
  id: string;
  type: "trigger" | "condition" | "action" | "output";
  label: string;
  x: number;
  y: number;
};

type LogicEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
};

const props = defineProps<{
  modeSummary: string;
}>();

const emit = defineEmits<{
  (event: "node-add", payload: LogicNode): void;
  (event: "node-delete", payload: { id: string }): void;
  (event: "edge-add", payload: LogicEdge): void;
  (event: "edge-delete", payload: { id: string }): void;
}>();

const nodes = ref<LogicNode[]>([
  { id: "node-1", type: "trigger", label: "OnAttack", x: 50, y: 50 },
  { id: "node-2", type: "condition", label: "Health > 50%", x: 200, y: 50 },
  { id: "node-3", type: "action", label: "CounterAttack", x: 350, y: 50 },
]);

const edges = ref<LogicEdge[]>([
  { id: "edge-1", source: "node-1", target: "node-2", label: "true" },
  { id: "edge-2", source: "node-2", target: "node-3", label: "true" },
]);

const selectedNodeId = ref<string>("");
const newNodeType = ref<LogicNode["type"]>("action");
const newNodeLabel = ref<string>("");
const edgeSource = ref<string>("");
const edgeTarget = ref<string>("");
const zoom = ref<number>(1);

const nodeTypeColors: Record<LogicNode["type"], string> = {
  trigger: "#e74c3c",
  condition: "#f39c12",
  action: "#3498db",
  output: "#2ecc71",
};

const nodeIds = computed(() => nodes.value.map((n) => n.id));

const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) ?? null);

const addNode = () => {
  if (!newNodeLabel.value.trim()) return;
  const id = `node-${Date.now()}`;
  const node: LogicNode = {
    id,
    type: newNodeType.value,
    label: newNodeLabel.value.trim(),
    x: 100 + Math.random() * 200,
    y: 100 + Math.random() * 100,
  };
  nodes.value.push(node);
  emit("node-add", node);
  newNodeLabel.value = "";
};

const deleteSelectedNode = () => {
  if (!selectedNodeId.value) return;
  nodes.value = nodes.value.filter((n) => n.id !== selectedNodeId.value);
  edges.value = edges.value.filter((e) => e.source !== selectedNodeId.value && e.target !== selectedNodeId.value);
  emit("node-delete", { id: selectedNodeId.value });
  selectedNodeId.value = "";
};

const addEdge = () => {
  if (!edgeSource.value || !edgeTarget.value || edgeSource.value === edgeTarget.value) return;
  const exists = edges.value.some((e) => e.source === edgeSource.value && e.target === edgeTarget.value);
  if (exists) return;
  const edge: LogicEdge = {
    id: `edge-${Date.now()}`,
    source: edgeSource.value,
    target: edgeTarget.value,
    label: "next",
  };
  edges.value.push(edge);
  emit("edge-add", edge);
};

const deleteEdge = (edgeId: string) => {
  edges.value = edges.value.filter((e) => e.id !== edgeId);
  emit("edge-delete", { id: edgeId });
};

const zoomIn = () => {
  zoom.value = Math.min(zoom.value * 1.2, 3);
};

const zoomOut = () => {
  zoom.value = Math.max(zoom.value / 1.2, 0.3);
};
</script>

<template>
  <section class="panel-section">
    <header class="logic-header">
      <h3>逻辑编排器</h3>
      <p class="summary">{{ modeSummary }}</p>
    </header>

    <div class="toolbar">
      <div class="zoom-controls">
        <button @click="zoomOut">-</button>
        <span>{{ (zoom * 100).toFixed(0) }}%</span>
        <button @click="zoomIn">+</button>
      </div>
      <div class="stats">
        <span>节点: {{ nodes.length }}</span>
        <span>连线: {{ edges.length }}</span>
      </div>
    </div>

    <div class="canvas-container">
      <svg class="logic-canvas" :style="{ transform: `scale(${zoom})` }">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#7f8c8d" />
          </marker>
        </defs>

        <g v-for="edge in edges" :key="edge.id">
          <line
            :x1="nodes.find((n) => n.id === edge.source)?.x ?? 0"
            :y1="(nodes.find((n) => n.id === edge.source)?.y ?? 0) + 20"
            :x2="nodes.find((n) => n.id === edge.target)?.x ?? 0"
            :y2="(nodes.find((n) => n.id === edge.target)?.y ?? 0) + 20"
            stroke="#7f8c8d"
            stroke-width="2"
            marker-end="url(#arrowhead)"
          />
          <text
            :x="((nodes.find((n) => n.id === edge.source)?.x ?? 0) + (nodes.find((n) => n.id === edge.target)?.x ?? 0)) / 2"
            :y="((nodes.find((n) => n.id === edge.source)?.y ?? 0) + (nodes.find((n) => n.id === edge.target)?.y ?? 0)) / 2 + 20"
            font-size="10"
            fill="#5d7280"
            text-anchor="middle"
          >
            {{ edge.label }}
          </text>
        </g>

        <g
          v-for="node in nodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          class="node-group"
          :class="{ selected: selectedNodeId === node.id }"
          @click="selectedNodeId = node.id"
        >
          <rect
            width="100"
            height="40"
            rx="6"
            :fill="nodeTypeColors[node.type]"
            stroke="white"
            stroke-width="2"
          />
          <text x="50" y="25" text-anchor="middle" fill="white" font-size="12" font-weight="500">
            {{ node.label }}
          </text>
          <text x="50" y="10" text-anchor="middle" fill="white" font-size="9" opacity="0.8">
            {{ node.type }}
          </text>
        </g>
      </svg>
    </div>

    <div class="editor-panel">
      <h4>添加节点</h4>
      <div class="input-row">
        <select v-model="newNodeType">
          <option value="trigger">触发器</option>
          <option value="condition">条件</option>
          <option value="action">动作</option>
          <option value="output">输出</option>
        </select>
        <input v-model="newNodeLabel" type="text" placeholder="节点名称" @keyup.enter="addNode" />
        <button @click="addNode">添加</button>
      </div>

      <h4>添加连线</h4>
      <div class="input-row">
        <select v-model="edgeSource">
          <option value="">源节点</option>
          <option v-for="id in nodeIds" :key="`src-${id}`" :value="id">{{ id }}</option>
        </select>
        <span>→</span>
        <select v-model="edgeTarget">
          <option value="">目标节点</option>
          <option v-for="id in nodeIds" :key="`tgt-${id}`" :value="id">{{ id }}</option>
        </select>
        <button @click="addEdge">连接</button>
      </div>

      <div v-if="selectedNode" class="selected-info">
        <h4>选中节点</h4>
        <p>ID: {{ selectedNode.id }}</p>
        <p>类型: {{ selectedNode.type }}</p>
        <p>标签: {{ selectedNode.label }}</p>
        <button @click="deleteSelectedNode" class="delete-btn">删除节点</button>
      </div>

      <div v-if="edges.length > 0" class="edge-list">
        <h4>连线列表</h4>
        <div v-for="edge in edges" :key="edge.id" class="edge-item">
          <span>{{ edge.source }} → {{ edge.target }}</span>
          <button @click="deleteEdge(edge.id)">删除</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
}

.logic-header h3 {
  margin: 0;
}

.summary {
  margin: 0;
  font-size: 13px;
  color: #5d7280;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.zoom-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.zoom-controls button {
  width: 28px;
  height: 28px;
  border: 1px solid #9ec0d2;
  background: #f4fafc;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.stats {
  display: flex;
  gap: 12px;
  color: #5d7280;
}

.canvas-container {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  height: 200px;
  overflow: hidden;
  background: #f8fbfd;
}

.logic-canvas {
  width: 100%;
  height: 100%;
  transform-origin: center;
}

.node-group {
  cursor: pointer;
}

.node-group:hover rect {
  stroke: #0d6c8d;
  stroke-width: 3;
}

.node-group.selected rect {
  stroke: #e74c3c;
  stroke-width: 3;
}

.editor-panel {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 12px;
  background: #f8fbfd;
  display: grid;
  gap: 10px;
}

.editor-panel h4 {
  margin: 0;
  font-size: 13px;
  color: #1e495f;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-row select,
.input-row input {
  padding: 6px 10px;
  border: 1px solid #c5d9e4;
  border-radius: 6px;
  font-size: 13px;
}

.input-row button {
  padding: 6px 12px;
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  border-radius: 6px;
  cursor: pointer;
}

.selected-info {
  border-top: 1px solid #d6e6ee;
  padding-top: 10px;
  font-size: 13px;
}

.selected-info p {
  margin: 4px 0;
}

.delete-btn {
  background: #e74c3c !important;
  color: white;
  border-color: #c0392b !important;
}

.edge-list {
  border-top: 1px solid #d6e6ee;
  padding-top: 10px;
}

.edge-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}

.edge-item button {
  padding: 2px 8px;
  font-size: 11px;
  border: 1px solid #c5d9e4;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}
</style>
