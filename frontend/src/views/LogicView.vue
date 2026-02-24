<script setup lang="ts">
import { useStudioStore } from '@/stores';
import LogicComposer from '@/components/LogicComposer.vue';
import ActionFormBuilder from '@/components/ActionFormBuilder.vue';

const studioStore = useStudioStore();

const submitDraftAction = async (values: Record<string, string>) => {
  await studioStore.submitDraftAction(values);
};

const dryRun = computed(() => studioStore.dryRun);
const actionSchema = computed(() => studioStore.actionSchema);
</script>

<template>
  <div class="logic-view logic-stack">
    <LogicComposer />
    <ActionFormBuilder :fields="actionSchema" @submit="submitDraftAction" />
    <div v-if="dryRun" class="dry-run-box">
      <p><strong>预演:</strong> {{ dryRun.allowed ? "允许" : "阻止" }} / {{ dryRun.txn_preview_id }}</p>
      <ul>
        <li v-for="gate in dryRun.gates" :key="gate.tier">
          {{ gate.tier }} · {{ gate.passed ? "通过" : "失败" }} · {{ gate.detail }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'LogicView'
};
</script>

<style scoped>
.logic-view {
  height: 100%;
  width: 100%;
}

.logic-stack {
  display: grid;
  gap: 10px;
}

.dry-run-box {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbfd;
}

.dry-run-box p {
  margin: 0 0 6px;
}

.dry-run-box ul {
  margin: 0;
  padding-left: 18px;
}
</style>
