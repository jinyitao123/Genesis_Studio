<script setup lang="ts">
import { computed, ref } from "vue";

type LogicNode = {
  id: string;
  label: string;
  kind: "trigger" | "gate" | "effect" | "aggregator";
};

const nodes = ref<LogicNode[]>([
  { id: "n1", label: "输入动作", kind: "trigger" },
  { id: "n2", label: "范围校验", kind: "gate" },
  { id: "n3", label: "伤害结算", kind: "effect" },
  { id: "n4", label: "遥测聚合", kind: "aggregator" },
]);

const breakpointId = ref<string>("");
const executionIndex = ref<number>(0);

const activeNode = computed(() => nodes.value[executionIndex.value] ?? null);

const toggleBreakpoint = (id: string) => {
  breakpointId.value = breakpointId.value === id ? "" : id;
};

const step = () => {
  if (nodes.value.length === 0) {
    executionIndex.value = 0;
    return;
  }
  executionIndex.value = (executionIndex.value + 1) % nodes.value.length;
};
</script>

<template>
  <section class="panel-section">
    <header class="composer-header">
      <h3>逻辑编排器</h3>
      <div class="actions">
        <button type="button" @click="step">单步</button>
        <span v-if="activeNode">当前节点: {{ activeNode.label }}</span>
      </div>
    </header>

    <div class="nodes-grid">
      <article
        v-for="node in nodes"
        :key="node.id"
        class="node"
        :class="[`kind-${node.kind}`, { active: activeNode?.id === node.id }]"
      >
        <div class="node-top">
          <strong>{{ node.label }}</strong>
          <button type="button" class="bp-btn" @click="toggleBreakpoint(node.id)">
            {{ breakpointId === node.id ? "断点开" : "断点" }}
          </button>
        </div>
        <small>{{ node.kind.toUpperCase() }}</small>
      </article>
    </div>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
}

.composer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.composer-header h3 {
  margin: 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.actions button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.actions span {
  font-size: 12px;
  color: #314e60;
}

.nodes-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.node {
  border: 1px solid #d2e4ec;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
  display: grid;
  gap: 4px;
}

.node-top {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}

.node strong {
  color: #143f56;
}

.node small {
  color: #5b7483;
}

.bp-btn {
  border: 1px solid #9db9c9;
  border-radius: 6px;
  background: #f8fbfd;
  color: #2a536b;
  font-size: 11px;
  padding: 2px 6px;
}

.node.active {
  box-shadow: 0 0 0 2px #7eb7d0;
}

.kind-trigger {
  border-left: 4px solid #0d6c8d;
}

.kind-gate {
  border-left: 4px solid #d69e2e;
}

.kind-effect {
  border-left: 4px solid #2f855a;
}

.kind-aggregator {
  border-left: 4px solid #805ad5;
}
</style>
