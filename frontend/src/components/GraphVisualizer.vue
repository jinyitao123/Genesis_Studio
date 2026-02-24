<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted, shallowRef } from "vue";
import type { ObjectTypePayload, EventPayload, GraphNodePayload, GraphEdgePayload, ViewMode } from "@/types";
import cytoscape, { type Core, type NodeSingular, type EdgeSingular } from "cytoscape";
import type CytoscapePopper from "cytoscape-popper";

// Declare cytoscape-popper extension
declare module "cytoscape" {
  interface Core {
    popper?: (element: NodeSingular) => CytoscapePopper;
  }
}

const props = withDefaults(
  defineProps<{
    objectTypes: ObjectTypePayload[];
    events?: EventPayload[];
    graphNodes?: GraphNodePayload[];
    graphEdges?: GraphEdgePayload[];
    projectionId?: string;
  }>(),
  {
    events: () => [],
    projectionId: "default",
  },
);

const emit = defineEmits<{
  (event: "node-create", payload: { node_id: string; label: string }): void;
  (event: "node-rename", payload: { node_id: string; label: string }): void;
  (event: "node-delete", payload: { node_id: string }): void;
  (event: "edge-create", payload: { source_id: string; target_id: string; label: string }): void;
  (event: "edge-delete", payload: { source_id: string; target_id: string; label: string }): void;
  (event: "node-select", payload: { node_id: string | null }): void;
}>();

const containerRef = ref<HTMLDivElement | null>(null);
const cyInstance = shallowRef<Core | null>(null);
const zoomPercent = ref<number>(55);
const viewMode = ref<ViewMode>("story");
const keyPathOnly = ref<boolean>(true);
const selectedNodeId = ref<string>("");
const newNodeId = ref<string>("");
const newNodeLabel = ref<string>("");
const edgeSourceId = ref<string>("");
const edgeTargetId = ref<string>("");
const edgeLabel = ref<string>("关联");

// Missing variables that were causing errors
const localNodes = computed(() => {
  if (!cyInstance.value) return [];
  return cyInstance.value.nodes().map((n) => ({
    id: n.id(),
    label: n.data("label") || n.id(),
  }));
});

const localEdges = computed(() => {
  if (!cyInstance.value) return [];
  return cyInstance.value.edges().map((e) => ({
    id: e.id(),
    source: e.data("source"),
    target: e.data("target"),
    label: e.data("label") || "",
  }));
});

const virtualizedNodes = computed(() => {
  // Return all visible nodes for now
  return localNodes.value;
});

const lodLevel = computed(() => {
  if (zoomPercent.value < 20) {
    return "粒子";
  }
  if (zoomPercent.value > 80) {
    return "完整";
  }
  return "图标+名称";
});

const nodeIds = computed(() => {
  if (!cyInstance.value) return [];
  return cyInstance.value.nodes().map((n) => n.id());
});

const selectedNode = computed(() => {
  if (!cyInstance.value || !selectedNodeId.value) return null;
  return cyInstance.value.getElementById(selectedNodeId.value);
});

const edgeText = (value: string) => {
  const normalized = value.trim().toLowerCase();
  if (normalized.includes("attack") || normalized.includes("engage") || normalized.includes("打击")) {
    return "正在攻击";
  }
  if (normalized.includes("command") || normalized.includes("控制") || normalized.includes("指挥")) {
    return "正在指挥";
  }
  if (normalized.includes("support") || normalized.includes("支援")) {
    return "正在支援";
  }
  if (normalized.includes("observe") || normalized.includes("侦查") || normalized.includes("scan")) {
    return "正在侦查";
  }
  return value || "存在关联";
};

const incomingCount = (nodeId: string) => {
  if (!cyInstance.value) return 0;
  return cyInstance.value.edges(`[target="${nodeId}"]`).length;
};

const outgoingCount = (nodeId: string) => {
  if (!cyInstance.value) return 0;
  return cyInstance.value.edges(`[source="${nodeId}"]`).length;
};

const visibleEdges = computed(() => {
  if (!cyInstance.value) return [];
  if (!keyPathOnly.value || !selectedNodeId.value) {
    return cyInstance.value.edges().map((e) => ({
      id: e.id(),
      source: e.data("source"),
      target: e.data("target"),
      label: e.data("label") || "",
    }));
  }
  return cyInstance.value
    .edges(`[source="${selectedNodeId.value}"], [target="${selectedNodeId.value}"]`)
    .map((e) => ({
      id: e.id(),
      source: e.data("source"),
      target: e.data("target"),
      label: e.data("label") || "",
    }));
});

const storyLines = computed(() => {
  if (!selectedNode.value) {
    return ["请选择一个对象，系统会解释它与其他对象的关系。"];
  }
  const nodeLabel = selectedNode.value.data("label") || selectedNodeId.value;
  const lines = visibleEdges.value
    .map((edge) => {
      const source = edge.source === selectedNodeId.value ? nodeLabel : undefined;
      const target = edge.target === selectedNodeId.value ? nodeLabel : undefined;
      const sourceLabel = source || nodeIds.value.find((id) => id === edge.source) || edge.source;
      const targetLabel = target || nodeIds.value.find((id) => id === edge.target) || edge.target;
      return `${sourceLabel}${edgeText(edge.label)}${targetLabel}`;
    })
    .slice(0, 6);
  if (lines.length === 0) {
    return [`${nodeLabel}当前没有关键关系。`];
  }
  return lines;
});

const storySummary = computed(() => {
  if (!selectedNode.value) {
    return "当前为全局概览。";
  }
  const nodeLabel = selectedNode.value.data("label") || selectedNodeId.value;
  const out = outgoingCount(selectedNodeId.value);
  const incoming = incomingCount(selectedNodeId.value);
  if (out === 0 && incoming === 0) {
    return `${nodeLabel}暂时独立运行。`;
  }
  return `${nodeLabel}对外影响${out}个对象，受${incoming}个对象影响。`;
});

const nodeKind = (nodeId: string) => {
  const inCount = incomingCount(nodeId);
  const outCount = outgoingCount(nodeId);
  if (outCount >= 2 && inCount >= 1) {
    return "枢纽";
  }
  if (outCount > inCount) {
    return "主动";
  }
  if (inCount > outCount) {
    return "被动";
  }
  return "独立";
};

const initCytoscape = () => {
  if (!containerRef.value) return;

  // Import popper dynamically if available
  let popperExt: typeof import("cytoscape-popper") | null = null;
  try {
    popperExt = require("cytoscape-popper");
  } catch {
    // Popper not available, continue without it
  }

  if (popperExt && popperExt.default) {
    cytoscape.use(popperExt.default);
  }

  cyInstance.value = cytoscape({
    container: containerRef.value,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#0d6c8d",
          "label": "data(label)",
          "color": "#1e495f",
          "text-valign": "center",
          "text-halign": "center",
          "font-size": "12px",
          "width": "60px",
          "height": "60px",
          "border-width": "2px",
          "border-color": "#2a8e72",
          "text-wrap": "wrap",
          "text-max-width": "80px",
        },
      },
      {
        selector: "node:selected",
        style: {
          "background-color": "#ff9f43",
          "border-color": "#e74c3c",
          "border-width": "3px",
        },
      },
      {
        selector: "edge",
        style: {
          width: "2px",
          "line-color": "#9ec0d2",
          "target-arrow-color": "#9ec0d2",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "label": "data(label)",
          "font-size": "10px",
          "color": "#38586a",
          "text-rotation": "autorotate",
          "text-margin-y": "-10px",
        },
      },
      {
        selector: 'node[kind="枢纽"]',
        style: { "background-color": "#9b59b6", "width": "80px", "height": "80px" },
      },
      {
        selector: 'node[kind="主动"]',
        style: { "background-color": "#3498db" },
      },
      {
        selector: 'node[kind="被动"]',
        style: { "background-color": "#e74c3c" },
      },
      {
        selector: 'node[kind="独立"]',
        style: { "background-color": "#95a5a6" },
      },
      {
        selector: ".highlighted",
        style: {
          "border-width": "4px",
          "border-color": "#f39c12",
          "background-color": "#f1c40f",
        },
      },
      {
        selector: ".dimmed",
        style: { opacity: "0.2" },
      },
    ],
    layout: {
      name: "cose",
      animate: true,
      animationDuration: 500,
      nodeRepulsion: 8000,
      idealEdgeLength: 100,
      edgeElasticity: 100,
      nestingFactor: 1.2,
      gravity: 0.25,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0,
    },
  });

  // Event handlers
  cyInstance.value.on("tap", "node", (event) => {
    const node = event.target as NodeSingular;
    selectNode(node.id());
  });

  cyInstance.value.on("tap", (event) => {
    if (event.target === cyInstance.value) {
      selectNode("");
    }
  });
};

const selectNode = (nodeId: string) => {
  selectedNodeId.value = nodeId;
  newNodeLabel.value = nodeId ? nodeIds.value.find((id) => id === nodeId) || "" : "";

  if (!cyInstance.value) return;

  // Highlight selected node and its neighbors
  cyInstance.value.elements().removeClass("highlighted dimmed");

  if (nodeId) {
    const node = cyInstance.value.getElementById(nodeId);
    node.addClass("highlighted");
    node.connectedEdges().addClass("highlighted");
    cyInstance.value.elements().not(`#${nodeId}`).not(node.connectedEdges()).addClass("dimmed");
  }

  emit("node-select", { node_id: nodeId || null });
};

const loadGraphData = () => {
  if (!cyInstance.value) return;

  const nodes: { data: { id: string; label: string; kind?: string } }[] = [];
  const edges: { data: { id: string; source: string; target: string; label: string } }[] = [];

  // Load from graphNodes/graphEdges or fallback to objectTypes/events
  if (props.graphNodes && props.graphNodes.length > 0) {
    props.graphNodes.forEach((item) => {
      nodes.push({
        data: { id: item.node_id, label: item.label },
      });
    });
  } else if (props.objectTypes.length > 0) {
    props.objectTypes.forEach((item) => {
      nodes.push({
        data: { id: item.type_uri, label: item.display_name },
      });
    });
  }

  if (props.graphEdges && props.graphEdges.length > 0) {
    props.graphEdges.forEach((item) => {
      edges.push({
        data: {
          id: item.edge_id,
          source: item.source_id,
          target: item.target_id,
          label: item.label,
        },
      });
    });
  } else if (props.events.length > 0) {
    props.events
      .filter((item) => item.source_id && item.target_id)
      .slice(0, 120)
      .forEach((item) => {
        edges.push({
          data: {
            id: item.event_id,
            source: String(item.source_id),
            target: String(item.target_id),
            label: item.action_id,
          },
        });
      });
  }

  // Calculate node kinds and add to nodes
  nodes.forEach((node) => {
    const inCount = edges.filter((e) => e.data.target === node.data.id).length;
    const outCount = edges.filter((e) => e.data.source === node.data.id).length;
    let kind = "独立";
    if (outCount >= 2 && inCount >= 1) kind = "枢纽";
    else if (outCount > inCount) kind = "主动";
    else if (inCount > outCount) kind = "被动";
    node.data.kind = kind;
  });

  // Batch add elements
  cyInstance.value.batch(() => {
    cyInstance.value.elements().remove();
    if (nodes.length > 0) {
      cyInstance.value.add(nodes);
    }
    if (edges.length > 0) {
      cyInstance.value.add(edges);
    }
  });

  // Run layout
  if (nodes.length > 0 || edges.length > 0) {
    cyInstance.value.layout({
      name: "cose",
      animate: true,
      animationDuration: 500,
    } as any).run();
  }

  // Select first node if none selected
  if (!selectedNodeId.value && nodes.length > 0) {
    selectNode(nodes[0].data.id);
  }
  if (!edgeSourceId.value && nodes.length > 0) {
    edgeSourceId.value = nodes[0].data.id;
  }
  if (!edgeTargetId.value && nodes.length > 1) {
    edgeTargetId.value = nodes[1].data.id;
  }
};

const syncZoom = () => {
  if (!cyInstance.value) return;
  zoomPercent.value = Math.round(cyInstance.value.zoom() * 100);
};

watch(
  () => [props.objectTypes, props.events, props.graphNodes, props.graphEdges],
  () => {
    loadGraphData();
  },
  { deep: true },
);

onMounted(() => {
  initCytoscape();
  loadGraphData();
});

onUnmounted(() => {
  if (cyInstance.value) {
    cyInstance.value.destroy();
  }
});

// Editor functions
const createNode = () => {
  const id = newNodeId.value.trim();
  const label = newNodeLabel.value.trim();
  if (!id || !label) return;
  if (nodeIds.value.includes(id)) return;

  if (!cyInstance.value) return;

  cyInstance.value.add({
    data: { id, label, kind: "独立" },
  });

  emit("node-create", { node_id: id, label });
  selectedNodeId.value = id;
  newNodeId.value = "";

  if (!edgeSourceId.value) edgeSourceId.value = id;
  if (!edgeTargetId.value) edgeTargetId.value = id;
};

const renameNode = () => {
  const label = newNodeLabel.value.trim();
  if (!selectedNodeId.value || !label) return;
  if (!cyInstance.value) return;

  const node = cyInstance.value.getElementById(selectedNodeId.value);
  node.data("label", label);
  emit("node-rename", { node_id: selectedNodeId.value, label });
};

const deleteNode = () => {
  if (!selectedNodeId.value) return;
  if (!cyInstance.value) return;

  const node = cyInstance.value.getElementById(selectedNodeId.value);
  node.remove();
  emit("node-delete", { node_id: selectedNodeId.value });
  selectedNodeId.value = "";
};

const createEdge = () => {
  const source = edgeSourceId.value;
  const target = edgeTargetId.value;
  const label = edgeLabel.value.trim() || "关联";
  if (!source || !target || source === target) return;
  if (!cyInstance.value) return;

  // Check if edge already exists
  const existing = cyInstance.value.edges(`[source="${source}"][target="${target}"]`);
  if (existing.length > 0) return;

  const edgeId = `edge-${Date.now()}`;
  cyInstance.value.add({
    data: { id: edgeId, source, target, label },
  });

  emit("edge-create", { source_id: source, target_id: target, label });
};

const removeEdge = (edgeId: string) => {
  if (!cyInstance.value) return;
  const edge = cyInstance.value.getElementById(edgeId);
  const source = edge.data("source");
  const target = edge.data("target");
  const label = edge.data("label") || "";
  edge.remove();
  emit("edge-delete", { source_id: source, target_id: target, label });
};
</script>

<template>
  <section class="panel-section">
    <header class="graph-header">
      <h3>图谱可视化</h3>
      <div class="meta">
        <span>投影: {{ projectionId }}</span>
        <span>细节层级: {{ lodLevel }}</span>
      </div>
    </header>

    <label class="zoom-control">
      <span>语义缩放</span>
      <input v-model.number="zoomPercent" type="range" min="1" max="100" />
      <span>{{ zoomPercent }}%</span>
    </label>

    <div class="mode-bar">
      <button type="button" :class="{ active: viewMode === 'story' }" @click="viewMode = 'story'">故事视图</button>
      <button type="button" :class="{ active: viewMode === 'relation' }" @click="viewMode = 'relation'">关系视图</button>
      <button type="button" :class="{ active: viewMode === 'technical' }" @click="viewMode = 'technical'">技术视图</button>
    </div>

    <div class="story-panel" v-if="viewMode === 'story'">
      <h4>当前关系解释</h4>
      <p>{{ storySummary }}</p>
      <ul>
        <li v-for="line in storyLines" :key="line">{{ line }}</li>
      </ul>
      <label class="key-toggle">
        <input v-model="keyPathOnly" type="checkbox" />
        <span>仅显示关键路径</span>
      </label>
    </div>

    <div class="viewport" ref="containerRef"></div>

    <section class="relation-panel" v-if="viewMode === 'relation'">
      <h4>关系总览</h4>
      <div class="edge-list" v-if="localEdges.length > 0">
        <div v-for="edge in localEdges.slice(0, 30)" :key="edge.id" class="edge-item">
          <span>
            {{ localNodes.find((item) => item.id === edge.source)?.label ?? edge.source }}
            →
            {{ localNodes.find((item) => item.id === edge.target)?.label ?? edge.target }}
            · {{ edgeText(edge.label) }}
          </span>
        </div>
      </div>
      <p v-else>当前没有可展示关系。</p>
    </section>

    <section class="editor" v-if="viewMode === 'technical'">
      <h4>图谱编辑</h4>
      <div class="editor-row">
        <input v-model="newNodeId" type="text" placeholder="节点ID，例如 unit.drone" />
        <input v-model="newNodeLabel" type="text" placeholder="节点名称，例如 无人机" />
        <button type="button" @click="createNode">新增节点</button>
        <button type="button" @click="renameNode">重命名节点</button>
        <button type="button" @click="deleteNode">删除节点</button>
      </div>
      <div class="editor-row">
        <select v-model="edgeSourceId">
          <option v-for="item in nodeIds" :key="`source-${item}`" :value="item">源: {{ item }}</option>
        </select>
        <select v-model="edgeTargetId">
          <option v-for="item in nodeIds" :key="`target-${item}`" :value="item">目标: {{ item }}</option>
        </select>
        <input v-model="edgeLabel" type="text" placeholder="关系，例如 关联" />
        <button type="button" @click="createEdge">新增关系</button>
      </div>
      <div class="edge-list" v-if="localEdges.length > 0">
        <div v-for="edge in localEdges.slice(0, 20)" :key="edge.id" class="edge-item">
          <span>{{ edge.source }} -> {{ edge.target }} · {{ edge.label }}</span>
          <button type="button" @click="removeEdge(edge.id)">删除</button>
        </div>
      </div>
      <p v-if="selectedNode">当前节点: {{ selectedNode.id }}</p>
    </section>

    <footer class="graph-footer">
      <span>可见节点: {{ localNodes.length }}</span>
      <span>关系数量: {{ localEdges.length }}</span>
    </footer>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.graph-header h3 {
  margin: 0;
}

.meta {
  display: grid;
  gap: 2px;
  text-align: right;
  font-size: 12px;
  color: #38586a;
}

.zoom-control {
  display: grid;
  gap: 6px;
}

.mode-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mode-bar button {
  border: 1px solid #9ec0d2;
  border-radius: 8px;
  background: #f4fafc;
  color: #1e495f;
  padding: 6px 12px;
  cursor: pointer;
}

.mode-bar button.active {
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
  border-color: #0d6c8d;
}

.graph-controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.graph-controls button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.story-panel,
.relation-panel {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbfd;
  display: grid;
  gap: 8px;
}

.story-panel h4,
.relation-panel h4,
.story-panel p {
  margin: 0;
}

.story-panel ul {
  margin: 0;
  padding-left: 18px;
}

.key-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #365364;
  font-size: 13px;
}

.viewport {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  background: linear-gradient(145deg, #fafdff, #f1f8fb);
  height: 320px;
  min-height: 200px;
  overflow: hidden;
}

.graph-footer {
  display: flex;
  justify-content: space-between;
  color: #4d6472;
  font-size: 12px;
}

.editor {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  gap: 8px;
  background: #f8fbfd;
}

.editor h4 {
  margin: 0;
  color: #163d52;
}

.editor-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.editor-row input,
.editor-row select {
  border: 1px solid #c5d9e4;
  border-radius: 8px;
  padding: 6px 8px;
}

.editor-row button,
.edge-item button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.edge-list {
  display: grid;
  gap: 6px;
}

.edge-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  border: 1px solid #d6e6ee;
  border-radius: 8px;
  padding: 6px 8px;
  background: #fff;
}
</style>
