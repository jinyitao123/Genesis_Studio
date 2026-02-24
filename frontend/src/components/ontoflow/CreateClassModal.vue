<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  existingNames: string[];
}>();

const emit = defineEmits<{
  confirm: [name: string, description: string];
  cancel: [];
}>();

const name = ref('');
const description = ref('');

const nameError = computed(() => {
  if (!name.value) return '';
  if (props.existingNames.includes(name.value.trim())) return '类名已存在';
  return '';
});
const canSubmit = computed(() => name.value.trim().length > 0 && !nameError.value);

function submit() {
  if (!canSubmit.value) return;
  emit('confirm', name.value.trim(), description.value.trim());
}
</script>

<template>
  <div class="of-modal-overlay" @click.self="emit('cancel')">
    <div class="of-modal" style="width:480px">
      <h3 class="of-modal__title">创建类</h3>
      <div class="of-field">
        <label class="of-label">类名 <span class="of-required">*</span></label>
        <input
          v-model="name"
          class="of-input"
          :class="{ 'of-input--error': nameError }"
          placeholder="输入类名（例如：Person）"
          @keyup.enter="submit"
        />
        <p v-if="nameError" class="of-error">{{ nameError }}</p>
      </div>
      <div class="of-field">
        <label class="of-label">描述</label>
        <textarea
          v-model="description"
          class="of-input of-textarea"
          placeholder="输入类描述（例如：表示现实中的个体）"
        />
      </div>
      <div class="of-modal__actions">
        <button class="of-btn of-btn--ghost" @click="emit('cancel')">Cancel</button>
        <button class="of-btn of-btn--primary" :disabled="!canSubmit" @click="submit">Create Class</button>
      </div>
    </div>
  </div>
</template>
