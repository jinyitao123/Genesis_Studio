<script setup lang="ts">
type EventPayload = {
  event_id: string;
  action_id: string;
  created_at: string;
};

defineProps<{
  events: EventPayload[];
}>();
</script>

<template>
  <section class="panel-section">
    <h3>时间线控制器</h3>
    <ol>
      <li v-for="item in events" :key="item.event_id">
        {{ item.action_id }} · {{ item.created_at }}
      </li>
    </ol>
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

.panel-section ol {
  margin: 0;
  padding-left: 18px;
}
</style>
