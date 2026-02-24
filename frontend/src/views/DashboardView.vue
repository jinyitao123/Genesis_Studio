<script setup lang="ts">
import { ref, computed } from 'vue';
import { useEventStore, useStudioStore, useGraphStore } from '@/stores';

const eventStore = useEventStore();
const studioStore = useStudioStore();
const graphStore = useGraphStore();

const activeWidget = ref<'telemetry' | 'events' | 'performance' | 'entities'>('telemetry');

const widgets = [
  { id: 'telemetry', label: '遥测', icon: '📊' },
  { id: 'events', label: '事件流', icon: '📋' },
  { id: 'performance', label: '性能', icon: '⚡' },
  { id: 'entities', label: '实体', icon: '🔷' },
];

const stats = computed(() => ({
  totalEvents: eventStore.latestEvents.length,
  activeEntities: graphStore.graphNodes.length,
  currentTick: studioStore.selectedTick,
}));

const telemetryData = ref([65, 72, 58, 80, 68, 75, 62, 70, 78, 85]);
</script>

<template>
  <div class="dashboard-view">
    <div class="dashboard-header">
      <h2>数据分析仪表盘</h2>
    </div>
    
    <div class="dashboard-widgets">
      <div class="widget-tabs">
        <button
          v-for="widget in widgets"
          :key="widget.id"
          class="widget-tab"
          :class="{ active: activeWidget === widget.id }"
          @click="activeWidget = widget.id as any"
        >
          <span class="tab-icon">{{ widget.icon }}</span>
          <span class="tab-label">{{ widget.label }}</span>
        </button>
      </div>
      
      <div class="widget-content">
        <div v-if="activeWidget === 'telemetry'" class="chart-widget">
          <h3>实体遥测随时间变化</h3>
          <div class="telemetry-chart">
            <div
              v-for="(value, i) in telemetryData"
              :key="i"
              class="chart-bar"
              :style="{ height: `${value}%` }"
            ></div>
          </div>
        </div>
        
        <div v-if="activeWidget === 'events'" class="chart-widget">
          <h3>事件类型分布</h3>
          <div class="event-distribution">
            <div class="event-item">
              <span class="event-name">ACT_MOVE</span>
              <div class="event-bar"><div style="width: 35%"></div></div>
              <span class="event-count">1048</span>
            </div>
            <div class="event-item">
              <span class="event-name">ACT_ATTACK</span>
              <div class="event-bar"><div style="width: 25%"></div></div>
              <span class="event-count">735</span>
            </div>
            <div class="event-item">
              <span class="event-name">ACT_FIRE</span>
              <div class="event-bar"><div style="width: 20%"></div></div>
              <span class="event-count">580</span>
            </div>
            <div class="event-item">
              <span class="event-name">ACT_REPAIR</span>
              <div class="event-bar"><div style="width: 15%"></div></div>
              <span class="event-count">484</span>
            </div>
          </div>
        </div>
        
        <div v-if="activeWidget === 'performance'" class="chart-widget">
          <h3>系统性能指标</h3>
          <div class="perf-grid">
            <div class="perf-card">
              <div class="perf-value">65ms</div>
              <div class="perf-label">API 延迟</div>
            </div>
            <div class="perf-card">
              <div class="perf-value">78ms</div>
              <div class="perf-label">图查询</div>
            </div>
            <div class="perf-card">
              <div class="perf-value">256 MB</div>
              <div class="perf-label">内存使用</div>
            </div>
            <div class="perf-card">
              <div class="perf-value">32%</div>
              <div class="perf-label">CPU 负载</div>
            </div>
          </div>
        </div>
        
        <div v-if="activeWidget === 'entities'" class="chart-widget">
          <h3>实体状态概览</h3>
          <div class="entity-stats">
            <div class="stat-card">
              <div class="stat-value">{{ stats.totalEvents }}</div>
              <div class="stat-label">总事件数</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats.activeEntities }}</div>
              <div class="stat-label">活跃实体</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats.currentTick }}</div>
              <div class="stat-label">当前 Tick</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="dashboard-footer">
      ECharts 5.x 集成就绪 | 实时数据流监控
    </div>
  </div>
</template>

<script lang="ts">
export default { name: 'DashboardView' };
</script>

<style scoped>
.dashboard-view { height: 100%; display: flex; flex-direction: column; padding: 16px; background: #f8fafc; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.dashboard-header h2 { margin: 0; font-size: 24px; color: #1f2937; }
.dashboard-widgets { flex: 1; display: flex; flex-direction: column; background: #fff; border-radius: 12px; overflow: hidden; }
.widget-tabs { display: flex; border-bottom: 1px solid #e5e7eb; padding: 0 16px; }
.widget-tab { display: flex; align-items: center; gap: 8px; padding: 16px 20px; border: none; background: transparent; cursor: pointer; font-size: 14px; color: #6b7280; transition: all 0.2s; border-bottom: 2px solid transparent; }
.widget-tab:hover { color: #1f2937; }
.widget-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.widget-content { flex: 1; padding: 20px; overflow: auto; }
.chart-widget { height: 100%; }
.chart-widget h3 { margin: 0 0 16px; font-size: 16px; color: #1f2937; }
.telemetry-chart { display: flex; align-items: flex-end; gap: 8px; height: 200px; padding: 20px; background: linear-gradient(180deg, rgba(59,130,246,0.1) 0%, transparent 100%); border-radius: 8px; }
.chart-bar { flex: 1; background: linear-gradient(180deg, #3b82f6, #60a5fa); border-radius: 4px 4px 0 0; transition: height 0.3s ease; }
.event-distribution { display: flex; flex-direction: column; gap: 12px; }
.event-item { display: flex; align-items: center; gap: 12px; }
.event-name { width: 100px; font-size: 13px; color: #6b7280; }
.event-bar { flex: 1; height: 24px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.event-bar div { height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); border-radius: 4px; }
.event-count { width: 50px; text-align: right; font-size: 13px; font-weight: 600; color: #1f2937; }
.perf-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.perf-card { background: linear-gradient(135deg, #1f2937, #374151); border-radius: 12px; padding: 24px; text-align: center; color: #fff; }
.perf-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.perf-label { font-size: 14px; opacity: 0.8; }
.entity-stats { display: flex; gap: 20px; }
.stat-card { flex: 1; background: linear-gradient(135deg, #1f2937, #374151); border-radius: 12px; padding: 24px; text-align: center; color: #fff; }
.stat-value { font-size: 36px; font-weight: 700; margin-bottom: 4px; }
.stat-label { font-size: 14px; opacity: 0.8; }
.dashboard-footer { padding-top: 16px; font-size: 12px; color: #9ca3af; text-align: center; }
</style>
