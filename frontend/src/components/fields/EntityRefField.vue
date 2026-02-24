<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { InspectorFieldSchema } from '@/types';
import { apiGet } from '@/api/client';

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
const isLoading = ref(false);
const searchResults = ref<Array<{ id: string; label: string }>>([]);
const selectedResult = ref<{ id: string; label: string } | null>(null);

// Mock entity types - in production, this would come from the schema
const entityTypes = computed(() => {
  // Default to looking for entities
  return [];
});

const placeholder = computed(() => props.field.placeholder || `搜索${props.field.label}...`);

async function searchEntities(query: string) {
  if (query.length < 2) {
    searchResults.value = [];
    return;
  }
  
  isLoading.value = true;
  try {
    // In production, call actual search API
    // const results = await apiGet<Array<{ id: string; label: string }>>(
    //   `/api/query/entities/search?q=${encodeURIComponent(query)}`
    // );
    
    // Mock results for demo
    searchResults.value = [
      { id: `${query}-1`, label: `${query} Entity 1` },
      { id: `${query}-2`, label: `${query} Entity 2` },
      { id: `${query}-3`, label: `${query} Entity 3` },
    ].filter(e => e.label.toLowerCase().includes(query.toLowerCase()));
  } catch {
    searchResults.value = [];
  } finally {
    isLoading.value = false;
  }
}

function selectResult(result: { id: string; label: string }) {
  searchQuery.value = result.label;
  selectedResult.value = result;
  emit('update:model-value', result.id);
  isOpen.value = false;
}

function clearSelection() {
  searchQuery.value = '';
  selectedResult.value = null;
  emit('update:model-value', '');
}

watch(searchQuery, (newQuery) => {
  if (isOpen.value) {
    searchEntities(newQuery);
  }
});

function toggleDropdown() {
  isOpen.value = !isOpen.value;
  if (isOpen.value && searchQuery.value) {
    searchEntities(searchQuery.value);
  }
}
</script>

<template>
  <div class="entity-ref-field" :class="{ 'has-error': error, 'is-open': isOpen }">
    <div class="search-input-wrapper">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        :placeholder="placeholder"
        @focus="toggleDropdown"
        @blur="setTimeout(() => isOpen = false, 200)"
      />
      <button 
        v-if="selectedResult" 
        type="button" 
        class="clear-btn"
        @click="clearSelection"
      >
        ×
      </button>
      <span v-if="isLoading" class="loading-spinner"></span>
    </div>
    
    <div v-if="isOpen && searchResults.length > 0" class="search-results">
      <div
        v-for="result in searchResults"
        :key="result.id"
        class="search-result-item"
        @click="selectResult(result)"
      >
        {{ result.label }}
      </div>
    </div>
    
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.entity-ref-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
}

.search-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}

.search-input:focus {
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

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e5e7eb;
  border-top-color: #0d6c8d;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.search-results {
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

.search-result-item {
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.search-result-item:hover {
  background: #f3f4f6;
}

.entity-ref-field.has-error .search-input {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
