<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { InspectorFieldSchema } from '@/types';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: string): void;
}>();

const searchQuery = ref(String(props.modelValue ?? ''));
const isOpen = ref(false);
const searchResults = ref<Array<{ id: string; label: string; type: string }>>([]);
const selectedLink = ref<{ id: string; label: string; type: string } | null>(null);

const placeholder = computed(() => props.field.placeholder || `搜索链接目标...`);

// Mock soft links - in production, this would query the ontology
const mockLinks = [
  { id: 'link-1', label: 'Tank Alpha', type: 'vehicle' },
  { id: 'link-2', label: 'Drone Beta', type: 'unit' },
  { id: 'link-3', label: 'Supply Depot', type: 'structure' },
  { id: 'link-4', label: 'Radar Station', type: 'sensor' },
];

function searchLinks(query: string) {
  if (query.length < 1) {
    searchResults.value = [];
    return;
  }
  
  // In production, call actual API
  // const results = await apiGet<Array<{ id: string; label: string; type: string }>>(
  //   `/api/query/links/search?q=${encodeURIComponent(query)}`
  // );
  
  searchResults.value = mockLinks.filter(l => 
    l.label.toLowerCase().includes(query.toLowerCase())
  );
}

function selectLink(link: { id: string; label: string; type: string }) {
  searchQuery.value = link.label;
  selectedLink.value = link;
  emit('update:model-value', link.id);
  isOpen.value = false;
}

function clearLink() {
  searchQuery.value = '';
  selectedLink.value = null;
  emit('update:model-value', '');
}

watch(searchQuery, () => {
  if (isOpen.value) {
    searchLinks(searchQuery.value);
  }
});
</script>

<template>
  <div class="soft-link-field" :class="{ 'has-error': error, 'is-open': isOpen }">
    <div class="link-input-wrapper">
      <input
        v-model="searchQuery"
        type="text"
        class="link-input"
        :placeholder="placeholder"
        @focus="isOpen = true; searchLinks(searchQuery)"
        @blur="setTimeout(() => isOpen = false, 200)"
      />
      <button 
        v-if="selectedLink" 
        type="button" 
        class="clear-btn"
        @click="clearLink"
      >
        ×
      </button>
    </div>
    
    <div v-if="isOpen && searchResults.length > 0" class="link-results">
      <div
        v-for="link in searchResults"
        :key="link.id"
        class="link-result-item"
        @click="selectLink(link)"
      >
        <span class="link-label">{{ link.label }}</span>
        <span class="link-type">{{ link.type }}</span>
      </div>
    </div>
    
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.soft-link-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
}

.link-input-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.link-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}

.link-input:focus {
  outline: none;
  border-color: #0d6c8d;
  box-shadow: 0 0 0 2px rgba(13, 108, 141, 0.1);
}

.clear-btn {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
}

.clear-btn:hover {
  color: #6b7280;
}

.link-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
}

.link-result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.link-result-item:hover {
  background: #f3f4f6;
}

.link-label {
  color: #374151;
}

.link-type {
  font-size: 11px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.soft-link-field.has-error .link-input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
