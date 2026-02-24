<script setup lang="ts">
import { ref, computed, shallowRef, h } from "vue";
import { VueFlow, useVueFlow, type Node, type Edge, type Connection, Handle, Position } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { MiniMap } from "@vue-flow/minimap";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";
import "@vue-flow/minimap/dist/style.css";
import type { LogicGateResult } from "@/types";

// Custom Logic Node Component
const LogicNodeComponent = {
  props: ["id", "data", "selected", "label"],
  setup(props: { id: string; data: any; selected: boolean }) {
    return () =>
      h("div", { class: ["custom-node", { selected: props.selected }] }, [
        h(Handle, { type: "target", position: Position.Left, class: "handle-target" }),
        h("div", { class: "node-header", style: { backgroundColor: getNodeColor(props.data.kind) } }, props.data.kind.toUpperCase()),
        h("div", { class: "node-body" }, [
          h("input", {
            type: "text",
            value: props.data.label,
            onInput: (e: Event) => {
              const target = e.target as HTMLInputElement;
              updateNodeLabel(props.id, target.value);
            },
            class: "node-label-input",
          }),
        ]),
        h("div", { class: "node-footer" }, [
          h("button", {
            type: "button",
            class: ["bp-btn", { active: props.data.breakpoint }],
            onClick: () => toggleBreakpoint(props.id),
          }, props.data.breakpoint ? "⏸ 断点" : "○ 断点"),
        ]),
        h(Handle, { type: "source", position: Position.Right, class: "handle-source" }),
      ]);
  },
};

const getNodeColor = (kind: string): string => {
  const colors: Record<string, string> = {
    trigger: "#0d6c8d",
    gate: "#d69e2e",
    effect: "#2f855a",
    aggregator: "#805ad5",
  };
  return colors[kind] || "#38586a";
};

const props = defineProps<{
  initialNodes?: Node<any>[];
  initialEdges?: Edge[];
}>();

const emit = defineEmits<{
  (event: "node-select", payload: { node_id: string | null }): void;
  (event: "connection-create", payload: { source: string; target: string }): void;
  (event: "breakpoint-toggle", payload: { node_id: string; enabled: boolean }): void;
  (event: "nodes-change", payload: { nodes: Node<any>[]; edges: Edge[] }): void;
}>();

const { addEdges, addNodes, onConnect, onNodeConnect, project } = useVueFlow();

const nodes = shallowRef<Node<any>[]>(
  props.initialNodes || [
    { id: "n1", type: "logic-node", position: { x: 100, y: 50 }, data: { label: "输入动作", kind: "trigger" } },
    { id: "n2", type: "logic-node", position: { x: 100, y: 180 }, data: { label: "范围校验", kind: "gate" } },
    { id: "n3", type: "logic-node", position: { x: 100, y: 310 }, data: { label: "伤害结算", kind: "effect" } },
    { id: "n4", type: "logic-node", position: { x: 350, y: 180 }, data: { label: "遥测聚合", kind: "aggregator" } },
  ]
);

const edges = shallowRef<Edge[]>(
  props.initialEdges || [
    { id: "e1-2", source: "n1", target: "n2", type: "smoothstep", animated: true },
    { id: "e2-3", source: "n2", target: "n3", type: "smoothstep", animated: true },
    { id: "e3-4", source: "n3", target: "n4", type: "smoothstep", animated: true },
  ]
);

const selectedNodeId = ref<string>("");
const executionIndex = ref<number>(0);

const activeNode = computed(() => {
  if (executionIndex.value >= 0 && executionIndex.value < nodes.value.length) {
    return nodes.value[executionIndex.value];
  }
  return null;
});

// Event handlers
onNodeConnect((params: Connection) => {
  if (params.source && params.target) {
    emit("connection-create", { source: params.source, target: params.target });
  }
});

const onNodeClick = (event: { node: Node<any> }) => {
  selectedNodeId.value = event.node.id;
  emit("node-select", { node_id: event.node.id });
};

const onPaneClick = () => {
  selectedNodeId.value = "";
  emit("node-select", { node_id: null });
};

const toggleBreakpoint = (nodeId: string) => {
  const node = nodes.value.find((n) => n.id === nodeId);
  if (node) {
    node.data.breakpoint = !node.data.breakpoint;
    emit("breakpoint-toggle", { node_id: nodeId, enabled: !!node.data.breakpoint });
  }
};

const updateNodeLabel = (nodeId: string, label: string) => {
  const node = nodes.value.find((n) => n.id === nodeId);
  if (node) {
    node.data.label = label;
    emit("nodes-change", { nodes: nodes.value, edges: edges.value });
  }
};

const step = () => {
  if (nodes.value.length === 0) {
    executionIndex.value = 0;
    return;
  }
  executionIndex.value = (executionIndex.value + 1) % nodes.value.length;
};

const addNode = (kind: string) => {
  const id = `n${Date.now()}`;
  const position = { x: Math.random() * 200 + 50, y: Math.random() * 200 + 50 };
  const labels: Record<string, string> = {
    trigger: "新触发器",
    gate: "新逻辑门",
    effect: "新效果",
    aggregator: "新聚合器",
  };
  const newNode: Node<any> = {
    id,
    type: "logic-node",
    position,
    data: { label: labels[kind] || "新节点", kind, breakpoint: false },
  };
  nodes.value = [...nodes.value, newNode];
  emit("nodes-change", { nodes: nodes.value, edges: edges.value });
};

const deleteSelectedNode = () => {
  if (!selectedNodeId.value) return;
  nodes.value = nodes.value.filter((n) => n.id !== selectedNodeId.value);
  edges.value = edges.value.filter((e) => e.source !== selectedNodeId.value && e.target !== selectedNodeId.value);
  emit("nodes-change", { nodes: nodes.value, edges: edges.value });
  selectedNodeId.value = "";
};
</script>

<template>
  <section class="panel-section composer-container">
    <header class="composer-header">
      <h3>逻辑编排器</h3>
      <div class="actions">
        <button type="button" @click="step" title="单步执行">▶▶</button>
        <button type="button" @click="addNode('trigger')" title="添加触发器">+触发器</button>
        <button type="button" @click="addNode('gate')" title="添加逻辑门">+逻辑门</button>
        <button type="button" @click="addNode('effect')" title="添加效果">+效果</button>
        <button type="button" @click="addNode('aggregator')" title="添加聚合器">+聚合器</button>
        <button type="button" @click="deleteSelectedNode" :disabled="!selectedNodeId" title="删除选中">删除</button>
        <span v-if="activeNode" class="execution-indicator">
          执行: <strong>{{ activeNode.data.label }}</strong>
        </span>
      </div>
    </header>

    <div class="flow-wrapper">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-viewport="{ zoom: 1 }"
        :min-zoom="0.2"
        :max-zoom="4"
        :node-types="['logic-node']"
        @node-click="onNodeClick"
        @pane-click="onPaneClick"
      >
        <Background pattern-color="#cde0e8" :gap="20" />
        <Controls />
        <MiniMap />
      </VueFlow>
    </div>

    <!-- Custom node template for Vue Flow -->
    <template id="logic-node-template">
      <div class="custom-node">
        <div class="node-header" :style="{ backgroundColor: getNodeColor(data.kind) }">
          <span class="node-kind">{{ data.kind.toUpperCase() }}</span>
        </div>
        <div class="node-body">
          <input
            type="text"
            :value="data.label"
            @input="(e) => updateNodeLabel(id, (e.target as HTMLInputElement).value)"
            class="node-label-input"
          />
        </div>
        <div class="node-footer">
          <button
            type="button"
            class="bp-btn"
            :class="{ active: data.breakpoint }"
            @click.stop="toggleBreakpoint(id)"
          >
            {{ data.breakpoint ? "⏸ 断点" : "○ 断点" }}
          </button>
        </div>
      </div>
    </template>

    <div class="node-list" v-if="nodes.length > 0">
      <h4>节点列表</h4>
      <div
        v-for="node in nodes"
        :key="node.id"
        class="node-item"
        :class="{ active: activeNode?.id === node.id }"
        @click="selectedNodeId = node.id; $emit('node-select', { node_id: node.id })"
      >
        <span class="node-dot" :style="{ backgroundColor: getNodeColor(node.data.kind) }"></span>
        <span class="node-label">{{ node.data.label }}</span>
        <span class="node-kind-badge">{{ node.data.kind }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.composer-container {
  min-height: 400px;
}

.composer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.composer-header h3 {
  margin: 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.actions button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.actions button:hover:not(:disabled) {
  background: #e0f0f8;
}

.execution-indicator {
  font-size: 12px;
  color: #314e60;
  margin-left: 8px;
}

.flow-wrapper {
  flex: 1;
  min-height: 300px;
  border: 1px solid #cde0e8;
  border-radius: 10px;
  overflow: hidden;
}

.node-list {
  border: 1px solid #cde0e8;
  border-radius: 8px;
  padding: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.node-list h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #38586a;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.node-item:hover {
  background: #f4fafc;
}

.node-item.active {
  background: #e0f0f8;
}

.node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.node-label {
  flex: 1;
  color: #143f56;
}

.node-kind-badge {
  font-size: 10px;
  color: #5b7483;
  text-transform: uppercase;
}

/* Vue Flow custom node styles */
:deep(.vue-flow__node.logic-node) {
  padding: 0;
  min-width: 140px;
}

:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  background: #0d6c8d;
}

:deep(.vue-flow__handle--target) {
  left: -4px;
}

:deep(.vue-flow__handle--source) {
  right: -4px;
}

.custom-node {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.node-header {
  padding: 4px 8px;
  color: #fff;
  font-size: 10px;
  font-weight: bold;
}

.node-body {
  padding: 8px;
}

.node-label-input {
  width: 100%;
  border: 1px solid #d2e4ec;
  border-radius: 4px;
  padding: 4px;
  font-size: 12px;
  text-align: center;
}

.node-footer {
  padding: 4px 8px;
  border-top: 1px solid #f1f8fb;
  display: flex;
  justify-content: center;
}

.bp-btn {
  border: 1px solid #9db9c9;
  border-radius: 4px;
  background: #f8fbfd;
  color: #2a536b;
  font-size: 10px;
  padding: 2px 6px;
  cursor: pointer;
}

.bp-btn.active {
  background: #ffeaa7;
  border-color: #fdcb6e;
}

.logic-node.active :deep(.node-header) {
  background: #f39c12;
}

.kind-trigger :deep(.node-header) {
  background: #0d6c8d;
}

.kind-gate :deep(.node-header) {
  background: #d69e2e;
}

.kind-effect :deep(.node-header) {
  background: #2f855a;
}

.kind-aggregator :deep(.node-header) {
  background: #805ad5;
}
</style>
