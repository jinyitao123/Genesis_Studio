<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  existingNames: string[];
}>();

const emit = defineEmits<{
  confirm: [name: string, type: 'string' | 'number', unique: boolean];
  cancel: [];
}>();

const name = ref('');
const type = ref<'string' | 'number'>('string');
const unique = ref(false);

const nameError = computed(() => {
  if (!name.value) return '';
  if (props.existingNames.includes(name.value.trim())) return '属性名已存在';
  return '';
});
const canSubmit = computed(() => name.value.trim().length > 0 && !nameError.value);

function submit() {
  if (!canSubmit.value) return;
  emit('confirm', name.value.trim(), type.value, unique.value);
}
</script>

<template>
  <div class="of-modal-overlay" @click.self="emit('cancel')">
    <div class="of-modal" style="width:400px">
      <h3 class="of-modal__title">添加属性</h3>
      <div class="of-field">
        <label class="of-label">属性名 <span class="of-required">*</span></label>
        <input
          v-model="name"
          class="of-input"
          :class="{ 'of-input--error': nameError }"
          placeholder="属性名（例如：age）"
          @keyup.enter="submit"
        />
        <p v-if="nameError" class="of-error">{{ nameError }}</p>
      </div>
      <div class="of-field">
        <label class="of-label">类型</label>
        <select v-model="type" class="of-input">
          <option value="string">A 字符串</option>
          <option value="number">123 数字</option>
        </select>
      </div>
      <div class="of-field of-field--row">
        <label class="of-label">唯一性</label>
        <button
          class="of-toggle"
          :class="{ 'of-toggle--on': unique }"
          @click="unique = !unique"
        >{{ unique ? '唯一' : '非唯一' }}</button>
      </div>
      <div class="of-modal__actions">
        <button class="of-btn of-btn--ghost" @click="emit('cancel')">Cancel</button>
        <button class="of-btn of-btn--primary" :disabled="!canSubmit" @click="submit">Add Property</button>
      </div>
    </div>
  </div>
</template>
