<script setup lang="ts">
defineProps<{
  projectionId: string;
  eventPoints: number;
}>();
</script>

<template>
  <section class="panel-section">
    <h3>图谱可视化</h3>
    <p>最新投影: {{ projectionId }}</p>
    <p>事件点数: {{ eventPoints }}</p>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 8px;
}

.panel-section h3 {
  margin: 0;
}

.panel-section p {
  margin: 0;
}
</style>
