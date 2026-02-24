<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import { useOntologyStore } from '@/stores';
import type {
  ObjectTypePayload,
  GraphNodePayload,
  GraphEdgePayload,
  InspectorFieldSchema,
  InspectorObjectSchema,
  FieldType,
} from '@/types';

// Import field type components
import StringField from './fields/StringField.vue';
import NumberField from './fields/NumberField.vue';
import BooleanField from './fields/BooleanField.vue';
import CoordinateField from './fields/CoordinateField.vue';
import EntityRefField from './fields/EntityRefField.vue';
import DateTimeField from './fields/DateTimeField.vue';
import EnumField from './fields/EnumField.vue';
import SoftLinkField from './fields/SoftLinkField.vue';
import DerivedField from './fields/DerivedField.vue';
import TimeSeriesField from './fields/TimeSeriesField.vue';

const props = defineProps<{
  selectedType?: ObjectTypePayload | null;
  selectedNode?: GraphNodePayload | null;
  selectedEdge?: GraphEdgePayload | null;
  editMode?: boolean;
  entityProperties?: Record<string, unknown>;
  linkProperties?: Record<string, unknown>;
  tick?: number;
  projectionLag?: number | null;
}>();

const emit = defineEmits<{
  (event: 'update:property', key: string, value: unknown): void;
  (event: 'save'): void;
  (event: 'cancel'): void;
  (event: 'load-schema', typeUri: string): void;
}>();

// Store
const ontologyStore = useOntologyStore();

// Inspector tabs
type InspectorTab = 'properties' | 'metadata' | 'actions' | 'history';

const activeTab = ref<InspectorTab>('properties');
const editing = ref(false);
const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle');
const schemaLoadError = ref<string | null>(null);

// Field type to component mapping
const FIELD_TYPE_COMPONENTS: Record<FieldType, any> = {
  string: StringField,
  integer: NumberField,
  float: NumberField,
  boolean: BooleanField,
  coordinate: CoordinateField,
  entity_ref: EntityRefField,
  datetime: DateTimeField,
  enum: EnumField,
  soft_link: SoftLinkField,
  derived: DerivedField,
  time_series: TimeSeriesField,
};

// Current inspector schema
const inspectorSchema = computed<InspectorObjectSchema | null>(() => {
  if (props.selectedType) {
    return ontologyStore.getInspectorSchema(props.selectedType.type_uri);
  }
  if (props.selectedNode?.type) {
    return ontologyStore.getInspectorSchema(props.selectedNode.type);
  }
  return null;
});

// Get field schema by name
function getFieldSchema(fieldName: string): InspectorFieldSchema | null {
  if (!inspectorSchema.value) return null;
  return inspectorSchema.value.fields.find(f => f.name === fieldName) || null;
}

// Dynamic field component for a property
function getFieldComponent(fieldName: string) {
  const schema = getFieldSchema(fieldName);
  if (!schema) return StringField;
  return FIELD_TYPE_COMPONENTS[schema.fieldType] || StringField;
}

// Property categories from schema
const propertyCategories = computed(() => {
  if (!inspectorSchema.value && !props.selectedNode && !props.selectedEdge) {
    return [];
  }

  const categories = [
    { id: 'static', label: '静态属性', fields: [] as InspectorFieldSchema[] },
    { id: 'timeseries', label: '时序属性', fields: [] as InspectorFieldSchema[] },
    { id: 'computed', label: '计算属性', fields: [] as InspectorFieldSchema[] },
  ];

  // Use schema fields if available
  if (inspectorSchema.value) {
    inspectorSchema.value.fields.forEach(field => {
      const storageType = getPropertyStorageType(field.fieldType);
      let category;
      switch (storageType) {
        case 'static':
          category = categories[0];
          break;
        case 'time_series':
          category = categories[1];
          break;
        case 'computed':
        case 'derived':
          category = categories[2];
          break;
        default:
          category = categories[0];
      }
      category.fields.push(field);
    });
  } else {
    // Fallback to props data with mock schema
    const fallbackFields: InspectorFieldSchema[] = [];
    
    if (props.selectedNode) {
      fallbackFields.push(
        { name: 'id', label: 'ID', fieldType: 'string', required: true, readonly: true },
        { name: 'type', label: '类型', fieldType: 'string', required: true, readonly: true },
        { name: 'status', label: '状态', fieldType: 'string', required: false, readonly: false },
      );
    }
    
    if (props.selectedEdge) {
      fallbackFields.push(
        { name: 'source', label: '源', fieldType: 'string', required: true, readonly: true },
        { name: 'target', label: '目标', fieldType: 'string', required: true, readonly: true },
        { name: 'type', label: '类型', fieldType: 'string', required: false, readonly: false },
      );
    }

    categories[0].fields = fallbackFields;
  }

  return categories.filter(c => c.fields.length > 0);
});

// Helper to determine storage type from field type
function getPropertyStorageType(fieldType: FieldType): 'static' | 'time_series' | 'computed' | 'derived' {
  const mapping: Record<FieldType, 'static' | 'time_series' | 'computed' | 'derived'> = {
    string: 'static',
    integer: 'static',
    float: 'static',
    boolean: 'static',
    coordinate: 'static',
    entity_ref: 'static',
    datetime: 'static',
    enum: 'static',
    soft_link: 'static',
    derived: 'derived',
    time_series: 'time_series',
  };
  return mapping[fieldType] || 'static';
}

// Edited values - reactive object that binds to form fields
const editedValues = computed({
  get: () => {
    const values: Record<string, unknown> = {};
    propertyCategories.value.forEach(cat => {
      cat.fields.forEach(field => {
        // Get value from props or default
        if (props.entityProperties && field.name in props.entityProperties) {
          values[field.name] = props.entityProperties[field.name];
        } else if (props.linkProperties && field.name in props.linkProperties) {
          values[field.name] = props.linkProperties[field.name];
        } else if (props.selectedNode && field.name === 'id') {
          values[field.name] = props.selectedNode.node_id;
        } else if (props.selectedNode && field.name === 'type') {
          values[field.name] = props.selectedNode.type;
        } else if (props.selectedEdge && field.name === 'source') {
          values[field.name] = props.selectedEdge.source_id;
        } else if (props.selectedEdge && field.name === 'target') {
          values[field.name] = props.selectedEdge.target_id;
        } else if (props.selectedEdge && field.name === 'type') {
          values[field.name] = props.selectedEdge.label;
        } else if (field.defaultValue !== undefined) {
          values[field.name] = field.defaultValue;
        }
      });
    });
    return values;
  },
  set: (newValues: Record<string, unknown>) => {
    // Values are updated through v-model on field components
  },
});

// Validation errors
const validationErrors = ref<Record<string, string>>({});

// Validate a field
function validateField(field: InspectorFieldSchema, value: unknown): string {
  if (field.required && (value === undefined || value === null || value === '')) {
    return `${field.label}不能为空`;
  }

  if (field.validation) {
    const { type, config } = field.validation;
    
    switch (type) {
      case 'regex':
        if (value && typeof value === 'string' && config.pattern && !new RegExp(config.pattern as string).test(value)) {
          return `${field.label}格式不正确`;
        }
        break;
      case 'range':
        const numValue = Number(value);
        if (!isNaN(numValue)) {
          if (config.min !== undefined && numValue < (config.min as number)) {
            return `${field.label}不能小于${config.min}`;
          }
          if (config.max !== undefined && numValue > (config.max as number)) {
            return `${field.label}不能大于${config.max}`;
          }
        }
        break;
    }
  }

  return '';
}

// Validate all fields
function validateAll(): boolean {
  const errors: Record<string, string> = {};
  let hasErrors = false;
  
  propertyCategories.value.forEach(cat => {
    cat.fields.forEach(field => {
      if (!field.readonly) {
        const error = validateField(field, editedValues.value[field.name]);
        if (error) {
          errors[field.name] = error;
          hasErrors = true;
        }
      }
    });
  });
  
  validationErrors.value = errors;
  return !hasErrors;
}

// Field change handler
function handleFieldChange(fieldName: string, value: unknown) {
  // Clear validation error when field changes
  if (validationErrors.value[fieldName]) {
    validationErrors.value[fieldName] = '';
  }
  
  // Emit change
  emit('update:property', fieldName, value);
}

// Bound actions from schema
const boundActions = computed(() => {
  if (inspectorSchema.value) {
    return inspectorSchema.value.bound_actions.map(action => ({
      id: action,
      label: action.replace('ACT_', '').replace(/_/g, ' ').toLowerCase(),
      icon: 'action',
    }));
  }
  
  // Fallback mock data
  if (props.selectedNode?.type === 'Drone') {
    return [
      { id: 'ACT_MOVE', label: '移动', icon: 'move' },
      { id: 'ACT_ATTACK', label: '攻击', icon: 'attack' },
      { id: 'ACT_SELF_DESTRUCT', label: '自毁', icon: 'explode', danger: true },
    ];
  }
  if (props.selectedType) {
    return [
      { id: 'ACT_CREATE', label: '创建实例', icon: 'plus' },
      { id: 'ACT_UPDATE', label: '更新属性', icon: 'edit' },
      { id: 'ACT_DELETE', label: '删除', icon: 'trash', danger: true },
    ];
  }
  return [];
});

// Start editing
function startEdit() {
  editing.value = true;
  activeTab.value = 'properties';
  validationErrors.value = {};
  
  // Load schema if not loaded
  if (props.selectedType?.type_uri) {
    ontologyStore.loadObjectTypeDetail(props.selectedType.type_uri);
  } else if (props.selectedNode?.type) {
    ontologyStore.loadObjectTypeDetail(props.selectedNode.type);
  }
}

// Cancel editing
function cancelEdit() {
  editing.value = false;
  validationErrors.value = {};
  emit('cancel');
}

// Save changes
async function saveChanges() {
  if (!validateAll()) {
    saveStatus.value = 'error';
    setTimeout(() => {
      saveStatus.value = 'idle';
    }, 2000);
    return;
  }
  
  saveStatus.value = 'saving';
  
  try {
    // Emit all property changes
    Object.entries(editedValues.value).forEach(([key, value]) => {
      emit('update:property', key, value);
    });
    
    saveStatus.value = 'saved';
    setTimeout(() => {
      saveStatus.value = 'idle';
      editing.value = false;
    }, 1500);
  } catch {
    saveStatus.value = 'error';
  }
}

// Format value for display
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') {
    if (value > 1000) return value.toLocaleString();
    if (value < 1 && value > 0) return `${(value * 100).toFixed(1)}%`;
    return String(value);
  }
  if (typeof value === 'boolean') return value ? '✓' : '✗';
  return String(value);
}

// Get value color based on status
function getValueColor(key: string, value: unknown): string {
  if (key === 'hp' && typeof value === 'number') {
    if (value < 30) return '#dc2626';
    if (value < 60) return '#f59e0b';
    return '#10b981';
  }
  if (key === 'battery' && typeof value === 'number') {
    if (value < 0.2) return '#dc2626';
    if (value < 0.5) return '#f59e0b';
    return '#10b981';
  }
  return 'inherit';
}

// Load schema on mount if type selected
onMounted(() => {
  if (props.selectedType?.type_uri) {
    ontologyStore.loadObjectTypeDetail(props.selectedType.type_uri);
  }
});
</script>

<template>
  <section class="inspector-panel">
    <header class="inspector-header">
      <h3>检查器</h3>
      <div class="inspector-controls">
        <button 
          v-if="!editing && (selectedNode || selectedEdge || selectedType)" 
          class="edit-btn"
          @click="startEdit"
        >
          编辑
        </button>
        <span v-if="selectedNode" class="selection-badge">
          {{ selectedNode.label }}
        </span>
        <span v-else-if="selectedType" class="selection-badge">
          {{ selectedType.display_name }}
        </span>
        <span v-else-if="selectedEdge" class="selection-badge">
          {{ selectedEdge.label }}
        </span>
      </div>
    </header>

    <!-- Schema loading error -->
    <div v-if="schemaLoadError" class="schema-error">
      {{ schemaLoadError }}
    </div>

    <nav class="tab-bar" v-if="selectedNode || selectedType || selectedEdge">
      <button 
        :class="{ active: activeTab === 'properties' }"
        @click="activeTab = 'properties'"
      >
        属性
      </button>
      <button 
        :class="{ active: activeTab === 'metadata' }"
        @click="activeTab = 'metadata'"
      >
        元数据
      </button>
      <button 
        v-if="boundActions.length > 0"
        :class="{ active: activeTab === 'actions' }"
        @click="activeTab = 'actions'"
      >
        动作
      </button>
      <button 
        v-if="selectedNode"
        :class="{ active: activeTab === 'history' }"
        @click="activeTab = 'history'"
      >
        历史
      </button>
    </nav>

    <!-- Properties Tab -->
    <div v-if="activeTab === 'properties'" class="tab-content">
      <div v-if="propertyCategories.length === 0" class="empty-state">
        <p>选择一个对象以查看属性</p>
      </div>
      
      <div v-else class="property-sections">
        <div v-for="category in propertyCategories" :key="category.id" class="property-category">
          <h4>{{ category.label }}</h4>
          
          <div class="property-list">
            <div 
              v-for="field in category.fields" 
              :key="field.name" 
              class="property-item"
              :class="{ 'has-error': validationErrors[field.name] }"
            >
              <label class="property-key">
                {{ field.label }}
                <span v-if="field.required && !field.readonly" class="required-mark">*</span>
              </label>
              
              <div class="property-value-wrapper">
                <!-- Dynamic field renderer -->
                <component
                  v-if="editing && !field.readonly"
                  :is="getFieldComponent(field.name)"
                  :field="field"
                  :model-value="editedValues[field.name]"
                  :error="validationErrors[field.name]"
                  @update:model-value="handleFieldChange(field.name, $event)"
                />
                
                <!-- Read-only display -->
                <span 
                  v-else 
                  class="property-value"
                  :style="{ color: getValueColor(field.name, editedValues[field.name]) }"
                >
                  {{ formatValue(editedValues[field.name]) }}
                </span>
                
                <span v-if="field.readonly" class="readonly-badge">只读</span>
              </div>
              
              <span v-if="validationErrors[field.name]" class="field-error">
                {{ validationErrors[field.name] }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="editing" class="edit-actions">
        <button class="save-btn" @click="saveChanges" :disabled="saveStatus === 'saving'">
          {{ saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '已保存' : '保存' }}
        </button>
        <button class="cancel-btn" @click="cancelEdit">取消</button>
      </div>
    </div>

    <!-- Metadata Tab -->
    <div v-if="activeTab === 'metadata'" class="tab-content">
      <div v-if="selectedNode" class="metadata-section">
        <h4>基本信息</h4>
        <div class="metadata-grid">
          <div class="metadata-item">
            <span class="meta-key">节点ID</span>
            <span class="meta-value mono">{{ selectedNode.node_id }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-key">类型</span>
            <span class="meta-value">{{ selectedNode.type || 'unknown' }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-key">创建时间</span>
            <span class="meta-value">{{ new Date().toLocaleString() }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-key">最后更新</span>
            <span class="meta-value">{{ new Date().toLocaleString() }}</span>
          </div>
        </div>

        <h4>仿真状态</h4>
        <div class="metadata-grid">
          <div class="metadata-item">
            <span class="meta-key">当前 Tick</span>
            <span class="meta-value">{{ tick || 0 }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-key">投影延迟</span>
            <span class="meta-value" :class="{ warning: (projectionLag || 0) > 100 }">
              {{ projectionLag ? `${projectionLag}ms` : '-' }}
            </span>
          </div>
        </div>
      </div>
      <div v-else-if="selectedType" class="metadata-section">
        <h4>类型定义</h4>
        <div class="metadata-grid">
          <div class="metadata-item">
            <span class="meta-key">Type URI</span>
            <span class="meta-value mono">{{ selectedType.type_uri }}</span>
          </div>
          <div class="metadata-item">
            <span class="meta-key">显示名称</span>
            <span class="meta-value">{{ selectedType.display_name }}</span>
          </div>
          <div v-if="inspectorSchema" class="metadata-item">
            <span class="meta-key">字段数</span>
            <span class="meta-value">{{ inspectorSchema.fields.length }}</span>
          </div>
          <div v-if="inspectorSchema" class="metadata-item">
            <span class="meta-key">访问级别</span>
            <span class="meta-value">{{ inspectorSchema.access_level || 'PUBLIC' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>选择一个对象以查看元数据</p>
      </div>
    </div>

    <!-- Actions Tab -->
    <div v-if="activeTab === 'actions'" class="tab-content">
      <div v-if="boundActions.length > 0" class="actions-grid">
        <button 
          v-for="action in boundActions" 
          :key="action.id"
          class="action-btn"
          :class="{ danger: action.danger }"
        >
          <span class="action-label">{{ action.label }}</span>
        </button>
      </div>
      <div v-else class="empty-state">
        <p>该对象无可用动作</p>
      </div>
    </div>

    <!-- History Tab -->
    <div v-if="activeTab === 'history'" class="tab-content">
      <div v-if="selectedNode" class="history-section">
        <h4>最近变更</h4>
        <ul class="history-list">
          <li class="history-item">
            <span class="history-time">T+{{ (tick || 0) - 5 }}</span>
            <span class="history-action">属性变更: hp 90 → 85</span>
          </li>
          <li class="history-item">
            <span class="history-time">T+{{ (tick || 0) - 12 }}</span>
            <span class="history-action">创建连接: → Tank_A</span>
          </li>
        </ul>
      </div>
      <div v-else class="empty-state">
        <p>选择一个实体以查看历史</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.inspector-panel {
  display: grid;
  gap: 12px;
  height: 100%;
}

.inspector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.inspector-header h3 {
  margin: 0;
  font-size: 14px;
  color: #1f2937;
}

.inspector-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.selection-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: #e9f4fa;
  color: #0d6c8d;
  border-radius: 999px;
}

.schema-error {
  background: #fef2f2;
  color: #dc2626;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
}

.edit-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.edit-btn:hover {
  background: #f9fafb;
}

.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #e5e7eb;
}

.tab-bar button {
  border: none;
  background: transparent;
  color: #6b7280;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab-bar button.active {
  color: #0d6c8d;
  border-bottom-color: #0d6c8d;
}

.tab-content {
  display: grid;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 24px;
  color: #9ca3af;
  font-size: 13px;
}

.property-category h4 {
  margin: 0 0 8px;
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.property-list {
  display: grid;
  gap: 6px;
}

.property-item {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px;
  align-items: start;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 6px;
}

.property-item.has-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.property-key {
  font-size: 12px;
  color: #374151;
  text-transform: capitalize;
  padding-top: 4px;
}

.required-mark {
  color: #dc2626;
  margin-left: 2px;
}

.property-value-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.property-value {
  font-size: 13px;
  font-weight: 500;
  font-family: 'Monaco', 'Consolas', monospace;
}

.field-error {
  grid-column: 1 / -1;
  color: #dc2626;
  font-size: 11px;
  margin-top: 4px;
}

.readonly-badge {
  font-size: 9px;
  padding: 1px 4px;
  background: #f3f4f6;
  color: #9ca3af;
  border-radius: 4px;
}

.edit-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.save-btn {
  flex: 1;
  border: none;
  background: #10b981;
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.cancel-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.metadata-section h4 {
  margin: 0 0 8px;
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
}

.metadata-grid {
  display: grid;
  gap: 6px;
}

.metadata-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.meta-key {
  color: #6b7280;
}

.meta-value {
  color: #374151;
  font-weight: 500;
}

.meta-value.mono {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 11px;
}

.meta-value.warning {
  color: #f59e0b;
}

.actions-grid {
  display: grid;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e5e7eb;
  background: #fff;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #0d6c8d;
}

.action-btn.danger {
  border-color: #fecaca;
  color: #dc2626;
}

.action-btn.danger:hover {
  background: #fef2f2;
}

.action-label {
  font-size: 13px;
  color: #374151;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}

.history-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #f3f4f6;
}

.history-time {
  color: #9ca3af;
  font-size: 11px;
  min-width: 50px;
}

.history-action {
  color: #374151;
}
</style>
