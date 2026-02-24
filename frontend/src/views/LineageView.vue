<script setup lang="ts">
import { useEventStore, useLineageStore } from '@/stores';
import LineageGraph from '@/components/LineageGraph.vue';

const eventStore = useEventStore();
const lineageStore = useLineageStore();

const transactions = computed(() => eventStore.transactions);
const selectedLineageTxn = computed({
  get: () => lineageStore.selectedTxnId,
  set: (val: string) => lineageStore.selectTransaction(val),
});
const lineageAggregate = computed(() => lineageStore.lineageAggregate);

const loadLineage = async (txnId: string) => {
  await lineageStore.loadLineage(txnId);
};
</script>

<template>
  <div class="lineage-view lineage-stack">
    <div class="txn-strip" v-if="transactions.length > 0">
      <button
        v-for="txn in transactions"
        :key="txn.txn_id"
        type="button"
        class="txn-btn"
        :class="{ active: selectedLineageTxn === txn.txn_id }"
        @click="loadLineage(txn.txn_id)"
      >
        {{ txn.action_id }} · {{ txn.status }}
      </button>
    </div>
    <LineageGraph :aggregate="lineageAggregate" />
  </div>
</template>

<script lang="ts">
import { computed } from 'vue';
export default {
  name: 'LineageView'
};
</script>

<style scoped>
.lineage-view {
  height: 100%;
  width: 100%;
}

.lineage-stack {
  display: grid;
  gap: 10px;
}

.txn-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.txn-btn {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.txn-btn.active {
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
  border-color: #0d6c8d;
}
</style>
