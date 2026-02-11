<script setup lang="ts">
import { computed, ref } from "vue";

type ObjectTypePayload = {
  type_uri: string;
  display_name: string;
};

type EventPayload = {
  event_id: string;
  action_id: string;
  created_at: string;
};

const props = defineProps<{
  projectionId: string;
  objectTypes: ObjectTypePayload[];
  events: EventPayload[];
}>();

const zoomPercent = ref<number>(55);

const lodLevel = computed(() => {
  if (zoomPercent.value < 20) {
    return "粒子";
  }
  if (zoomPercent.value > 80) {
    return "完整";
  }
  return "图标+名称";
});

const virtualizedNodes = computed(() => props.objectTypes.slice(0, 80));
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

    <div class="viewport">
      <article v-for="item in virtualizedNodes" :key="item.type_uri" class="node-card">
        <strong>{{ item.display_name }}</strong>
        <small>{{ item.type_uri }}</small>
      </article>
    </div>

    <footer class="graph-footer">
      <span>可见节点: {{ virtualizedNodes.length }}</span>
      <span>最近事件: {{ events.length }}</span>
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

.viewport {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  background: linear-gradient(145deg, #fafdff, #f1f8fb);
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  max-height: 280px;
  overflow: auto;
}

.node-card {
  border: 1px solid #d2e4ec;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
  display: grid;
  gap: 2px;
}

.node-card small {
  color: #5d7280;
}

.graph-footer {
  display: flex;
  justify-content: space-between;
  color: #4d6472;
  font-size: 12px;
}
</style>
