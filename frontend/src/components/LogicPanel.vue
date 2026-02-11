<script setup lang="ts">
defineProps<{
  modeSummary: string;
}>();
</script>

<template>
  <section class="panel-section">
    <h3>逻辑编排器</h3>
    <p>{{ modeSummary }}</p>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 8px;
}

.panel-section h3,
.panel-section p {
  margin: 0;
}
</style>
