<script setup lang="ts">
defineProps<{
  payload: Record<string, unknown> | null;
}>();
</script>

<template>
  <section class="panel-section">
    <h3>检查器</h3>
    <pre>{{ JSON.stringify(payload, null, 2) }}</pre>
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

.panel-section pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
