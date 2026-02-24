<script setup lang="ts">
import type { TabId, TabItem } from "@/types";

defineProps<{
  modelValue: TabId;
  tabs: TabItem[];
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: TabId): void;
}>();

const chooseTab = (value: TabId) => {
  emit("update:modelValue", value);
};
</script>

<template>
  <nav class="tabbar">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="tab-btn"
      :class="{ active: modelValue === tab.id }"
      @click="chooseTab(tab.id)"
      type="button"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>

<style scoped>
.tabbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab-btn {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.tab-btn.active {
  border-color: #0d6c8d;
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
}
</style>
