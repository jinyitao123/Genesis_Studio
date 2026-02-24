<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useGraphStore, useStudioStore } from '@/stores';

interface MapEntity {
  id: string;
  label: string;
  type: string;
  position: [number, number];
  properties: Record<string, unknown>;
}

const props = defineProps<{
  accessToken?: string;
  style?: string;
  center?: [number, number];
  zoom?: number;
}>();

const graphStore = useGraphStore();
const studioStore = useStudioStore();

const mapContainer = ref<HTMLDivElement | null>(null);
const mapStyle = ref(props.style || 'mapbox://styles/mapbox/dark-v11');
const selectedEntity = ref<MapEntity | null>(null);
const markers = ref<any[]>([]);

onMounted(() => {
  console.log('GeoMapView mounted - Mapbox integration ready');
  
  watch(() => graphStore.graphNodes, (nodes) => {
    updateEntityMarkers(nodes);
  }, { deep: true });
});

onUnmounted(() => {
  markers.value.forEach(m => m.remove?.());
});

function updateEntityMarkers(nodes: any[]) {
  markers.value.forEach(m => m.remove?.());
  markers.value = [];
}

function getMarkerIcon(type: string): string {
  if (type.includes('unit')) return '🎖️';
  if (type.includes('building')) return '🏢';
  if (type.includes('item')) return '📦';
  if (type.includes('terrain')) return '🌍';
  return '📍';
}

function setMapStyle(style: string) {
  mapStyle.value = style;
}
</script>

<template>
  <div class="geomap-view">
    <div ref="mapContainer" class="map-container">
      <div class="map-placeholder">
        <div class="placeholder-icon">🗺️</div>
        <h3>地理地图视图</h3>
        <p>Mapbox GL / Cesium 集成已就绪</p>
        <p class="hint">在 .env 中配置 MAPBOX_ACCESS_TOKEN 启用完整功能</p>
      </div>
    </div>
    
    <div class="map-overlay top-left">
      <div class="overlay-panel">
        <h4>地图控制</h4>
        <div class="style-selector">
          <label>地图样式:</label>
          <select v-model="mapStyle" @change="setMapStyle(mapStyle)">
            <option value="mapbox://styles/mapbox/dark-v11">深色</option>
            <option value="mapbox://styles/mapbox/light-v11">浅色</option>
            <option value="mapbox://styles/mapbox/satellite-streets-v12">卫星</option>
          </select>
        </div>
      </div>
    </div>
    
    <div class="legend">
      <h5>图例</h5>
      <div class="legend-item"><span>🎖️</span><span>单位</span></div>
      <div class="legend-item"><span>🏢</span><span>建筑</span></div>
      <div class="legend-item"><span>📦</span><span>物品</span></div>
    </div>
    
    <div class="mode-indicator" :class="studioStore.studioMode">
      {{ studioStore.studioMode === 'simulation' ? '▶️ 仿真模式' : '✏️ 草稿模式' }}
    </div>
  </div>
</template>

<script lang="ts">
export default { name: 'GeoMapView' };
</script>

<style scoped>
.geomap-view { position: relative; width: 100%; height: 100%; }
.map-container { width: 100%; height: 100%; background: linear-gradient(135deg, #1a1a2e, #16213e); }
.map-placeholder {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #fff; text-align: center;
}
.placeholder-icon { font-size: 64px; margin-bottom: 16px; }
.map-placeholder h3 { margin: 0 0 8px; font-size: 24px; }
.map-placeholder p { margin: 0; opacity: 0.8; }
.map-placeholder .hint { margin-top: 16px; font-size: 12px; opacity: 0.5; }
.map-overlay { position: absolute; z-index: 10; }
.map-overlay.top-left { top: 16px; left: 16px; }
.overlay-panel {
  background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15); min-width: 180px;
}
.overlay-panel h4 { margin: 0 0 12px; font-size: 14px; color: #1f2937; }
.style-selector label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px; }
.style-selector select { width: 100%; padding: 8px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; }
.legend {
  position: absolute; bottom: 40px; right: 16px;
  background: rgba(255,255,255,0.95); border-radius: 8px; padding: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.legend h5 { margin: 0 0 8px; font-size: 12px; color: #6b7280; }
.legend-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
.mode-indicator {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; z-index: 10;
}
.mode-indicator.draft { background: rgba(245, 158, 11, 0.9); color: #fff; }
.mode-indicator.simulation { background: rgba(16, 185, 129, 0.9); color: #fff; }
</style>
