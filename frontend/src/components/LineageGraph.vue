<script setup lang="ts">
import { computed } from "vue";

type LineageAggregate = {
  lineage: {
    transaction: Record<string, unknown>;
    primary_event: Record<string, unknown> | null;
    compensation_event: Record<string, unknown> | null;
  };
  bus_events: Record<string, unknown>[];
};

const props = defineProps<{
  aggregate: LineageAggregate | null;
}>();

const lineageNodes = computed(() => {
  if (!props.aggregate) {
    return [];
  }
  const transaction = props.aggregate.lineage.transaction;
  const primary = props.aggregate.lineage.primary_event;
  const compensation = props.aggregate.lineage.compensation_event;

  const nodes = [
    {
      id: String(transaction.txn_id ?? "unknown-txn"),
      type: "动作",
      label: String(transaction.action_id ?? "未知动作"),
    },
  ];

  if (primary) {
    nodes.push({
      id: String(primary.event_id ?? "primary-event"),
      type: "效果",
      label: String(primary.action_id ?? "主事件"),
    });
  }

  if (compensation) {
    nodes.push({
      id: String(compensation.event_id ?? "comp-event"),
      type: "状态变化",
      label: String(compensation.action_id ?? "补偿"),
    });
  }

  return nodes;
});

const lineageEdges = computed(() => {
  if (lineageNodes.value.length <= 1) {
    return [];
  }
  const edges: { from: string; to: string }[] = [];
  for (let index = 0; index < lineageNodes.value.length - 1; index += 1) {
    edges.push({
      from: lineageNodes.value[index].id,
      to: lineageNodes.value[index + 1].id,
    });
  }
  return edges;
});
</script>

<template>
  <section class="panel-section">
    <h3>事务追溯图</h3>
    <p v-if="!aggregate">暂无事务追溯数据。</p>

    <div v-else class="dag-canvas">
      <article v-for="node in lineageNodes" :key="node.id" class="node">
        <strong>{{ node.type }}</strong>
        <span>{{ node.label }}</span>
        <small>{{ node.id }}</small>
      </article>
    </div>

    <ul v-if="lineageEdges.length > 0" class="edge-list">
      <li v-for="edge in lineageEdges" :key="`${edge.from}:${edge.to}`">{{ edge.from }} -> {{ edge.to }}</li>
    </ul>

    <p v-if="aggregate">总线事件数: {{ aggregate.bus_events.length }}</p>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
}

.panel-section h3,
.panel-section p {
  margin: 0;
}

.dag-canvas {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f9fcfe;
  display: grid;
  gap: 8px;
}

.node {
  border: 1px solid #c6dce7;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
  display: grid;
  gap: 2px;
}

.node strong {
  color: #15425a;
}

.node small {
  color: #5c7381;
}

.edge-list {
  margin: 0;
  padding-left: 18px;
  color: #365364;
}
</style>
