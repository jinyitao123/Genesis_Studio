<script setup lang="ts">
import { computed, ref, watch } from "vue";

type ActionField = {
  name: string;
  label: string;
  input: "text" | "number" | "select";
  required?: boolean;
  options?: string[];
  defaultValue?: string;
};

const props = defineProps<{
  fields: ActionField[];
}>();

const emit = defineEmits<{
  (event: "submit", values: Record<string, string>): void;
}>();

const values = ref<Record<string, string>>(
  Object.fromEntries(props.fields.map((field) => [field.name, field.defaultValue ?? ""])),
);
const errors = ref<Record<string, string>>({});
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

const validateField = (field: ActionField, value: string) => {
  if (field.required && !value.trim()) {
    return `${field.label}不能为空`;
  }
  if (field.input === "number" && value.trim() && Number.isNaN(Number(value))) {
    return `${field.label}必须是数字`;
  }
  return "";
};

const validateAll = () => {
  const nextErrors: Record<string, string> = {};
  for (const field of props.fields) {
    const err = validateField(field, values.value[field.name] ?? "");
    if (err) {
      nextErrors[field.name] = err;
    }
  }
  errors.value = nextErrors;
  return Object.keys(nextErrors).length === 0;
};

const submit = () => {
  if (!validateAll()) {
    return;
  }
  emit("submit", { ...values.value });
};

const hasErrors = computed(() => Object.keys(errors.value).length > 0);

watch(
  values,
  () => {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      validateAll();
    }, 300);
  },
  { deep: true },
);
</script>

<template>
  <section class="panel-section">
    <header>
      <h3>动作表单构建器</h3>
      <p>基于 Schema 的输入表单，300ms 实时校验。</p>
    </header>

    <form class="form-grid" @submit.prevent="submit">
      <label v-for="field in fields" :key="field.name" class="field">
        <span>{{ field.label }}</span>
        <select v-if="field.input === 'select'" v-model="values[field.name]">
          <option v-for="option in field.options ?? []" :key="option" :value="option">{{ option }}</option>
        </select>
        <input
          v-else
          v-model="values[field.name]"
          :type="field.input === 'number' ? 'number' : 'text'"
          :placeholder="field.label"
        />
        <small v-if="errors[field.name]" class="error">{{ errors[field.name] }}</small>
      </label>

      <button type="submit" :disabled="hasErrors">执行预演</button>
    </form>
  </section>
</template>

<style scoped>
.panel-section {
  display: grid;
  gap: 10px;
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbfd;
}

header h3 {
  margin: 0;
}

header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #486171;
}

.form-grid {
  display: grid;
  gap: 8px;
}

.field {
  display: grid;
  gap: 4px;
}

.field span {
  font-size: 13px;
  color: #254256;
}

.field input,
.field select {
  border: 1px solid #c5d9e4;
  border-radius: 8px;
  padding: 6px 8px;
  background: #fff;
}

.error {
  color: #c53030;
  font-size: 12px;
}

button {
  border: 1px solid #0d6c8d;
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
