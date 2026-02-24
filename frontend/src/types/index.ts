// =============================================================================
// Genesis Studio — Shared TypeScript Types
// Generated from PRP v3.0 + Gap Analysis
// =============================================================================

// -----------------------------------------------------------------------------
// Core Domain Types
// -----------------------------------------------------------------------------

/** Simulation tick number */
export type Tick = number;

/** Universally unique identifier */
export type UUID = string;

/** Object Type URI following reverse domain notation */
export type TypeURI = string;

/** User/actor identifier */
export type SubjectID = string;

/** Transaction identifier */
export type TxnID = string;

/** Event identifier */
export type EventID = string;

/** Graph node/edge identifier */
export type GraphID = string;

// -----------------------------------------------------------------------------
// Studio Mode (Context Switcher)
// -----------------------------------------------------------------------------

export type StudioMode = 'draft' | 'simulation';

/** Extended Tab IDs including new GeoMap and Dashboard tabs */
export type TabId = 
  | 'graph' 
  | 'timeline' 
  | 'logic' 
  | 'lineage' 
  | 'inspector' 
  | 'proposals' 
  | 'copilot' 
  | 'ops'
  | 'geomap'
  | 'dashboard';

export interface TabItem {
  id: TabId;
  label: string;
  icon?: string;
}

// -----------------------------------------------------------------------------
// Health & Status Types
// -----------------------------------------------------------------------------

export interface HealthPayload {
  status: 'ok' | 'degraded' | 'error';
  service: string;
  timestamp?: string;
  version?: string;
  details?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Object Types (OTD) - PRP §3.1
// -----------------------------------------------------------------------------

export interface PropertyDefinition {
  name: string;
  type: 'string' | 'integer' | 'float' | 'boolean' | 'coordinate' | 'time_series' | 'soft_link' | 'derived';
  storage: 'static' | 'time_series' | 'computed' | 'soft_link' | 'derived';
  default_value?: unknown;
  validators?: PropertyValidator[];
  index?: 'none' | 'index' | 'fulltext' | 'composite';
  immutable?: boolean;
}

export interface PropertyValidator {
  type: 'regex' | 'range' | 'enum' | 'custom';
  config: Record<string, unknown>;
}

export interface ObjectTypeDefinition {
  type_uri: TypeURI;
  schema_version: string;
  display_name: string;
  parent_type?: TypeURI;
  implements?: string[];
  sealed?: boolean;
  abstract?: boolean;
  icon?: {
    default: string;
    condition?: string;
  };
  tags: string[];
  access_control: AccessControl;
  properties: Record<string, PropertyDefinition>;
  bound_actions: string[];
  lifecycle_hooks?: {
    on_spawn?: string;
    on_destroy?: string;
  };
}

export interface ObjectTypePayload {
  type_uri: TypeURI;
  display_name: string;
  parent_type?: TypeURI;
  schema_version?: string;
  tags?: string[];
}

export interface ObjectInstance {
  object_id: UUID;
  object_type: TypeURI;
  properties: Record<string, unknown>;
  location?: Coordinate;
  created_at: string;
  updated_at: string;
}

// -----------------------------------------------------------------------------
// Link Types (LTD) - PRP §3.2
// -----------------------------------------------------------------------------

export type LinkType = 'directed' | 'undirected' | 'bidirectional';

export type CardinalityType = 'one_to_one' | 'one_to_many' | 'many_to_many' | 'zero_or_one';

export interface LinkTypeDefinition {
  link_type_uri: string;
  display_name: string;
  source_type_constraint: string;
  target_type_constraint: string;
  directionality: LinkType;
  cardinality: {
    type: CardinalityType;
    max_fan_out?: number;
  };
  properties: Record<string, PropertyDefinition>;
  lifecycle?: {
    on_create?: string;
    on_update?: string;
    on_destroy?: string;
    on_expire?: string;
    transient?: boolean;
  };
}

export interface LinkInstance {
  link_id: UUID;
  link_type: string;
  source_id: UUID;
  target_id: UUID;
  properties: Record<string, unknown>;
  created_at: string;
  expires_at?: string;
}

// -----------------------------------------------------------------------------
// Coordinate & Location Types
// -----------------------------------------------------------------------------

export interface Coordinate {
  x: number;
  y: number;
  z?: number;
  crs?: string; // Coordinate Reference System
}

// -----------------------------------------------------------------------------
// Action Dispatch - PRP §4
// -----------------------------------------------------------------------------

export type ActionID = string;

export interface ActionField {
  name: string;
  label: string;
  input: 'text' | 'number' | 'select' | 'entity_ref' | 'coordinate' | 'datetime';
  required?: boolean;
  options?: string[];
  defaultValue?: string;
  constraints?: {
    type?: string;
    min?: number;
    max?: number;
    pattern?: string;
  };
}

export interface ActionDispatch {
  action_id: ActionID;
  source_id?: UUID | null;
  target_id?: UUID | null;
  actor: SubjectID;
  payload: Record<string, unknown>;
  traceparent?: string;
  correlation_id?: string;
  causation_id?: string;
}

export interface LogicGateResult {
  tier: 'L0' | 'L1' | 'L2' | 'L3' | 'L4';
  passed: boolean;
  detail: string;
}

export interface DispatchDryRunResponse {
  allowed: boolean;
  txn_preview_id: string;
  estimated_effects: string[];
  gates: LogicGateResult[];
}

// -----------------------------------------------------------------------------
// Event & Transaction Types - PRP §4.1, §6.3
// -----------------------------------------------------------------------------

export interface ActionEvent {
  event_id: EventID;
  action_id: ActionID;
  source_id?: UUID | null;
  target_id?: UUID | null;
  actor: SubjectID;
  payload: Record<string, unknown>;
  created_at: string;
  tick: Tick;
}

export interface EventPayload {
  event_id: EventID;
  action_id: ActionID;
  created_at: string;
  source_id?: UUID | null;
  target_id?: UUID | null;
  payload?: Record<string, unknown>;
  actor?: string;
}

export interface DispatchTransactionRecord {
  txn_id: TxnID;
  action_id: ActionID;
  actor: SubjectID;
  status: 'pending' | 'committed' | 'reverted' | 'failed';
  event_id: EventID | null;
  compensation_event_id: EventID | null;
  gates: LogicGateResult[];
  created_at: string;
}

export interface TransactionPayload {
  txn_id: TxnID;
  action_id: ActionID;
  status: string;
  event_id: string | null;
  created_at?: string;
}

// -----------------------------------------------------------------------------
// Saga & Compensation - PRP §4.2
// -----------------------------------------------------------------------------

export interface SagaStateResponse {
  txn_id: TxnID;
  state: 'DISPATCHED' | 'COMPENSATED' | 'FAILED';
  steps: string[];
  recoverable: boolean;
  compensation_event_id: EventID | null;
}

export interface RevertTransactionResponse {
  txn_id: TxnID;
  status: 'reverted' | 'failed';
  compensation_event_id: EventID | null;
}

// -----------------------------------------------------------------------------
// Projection & Time Travel - PRP §6.4, §11
// -----------------------------------------------------------------------------

export interface ProjectionSnapshot {
  projection_id: string;
  tick: Tick;
  created_at: string;
  events_count: number;
}

export interface ProjectionLag {
  lag: number;
  stream_event_count: number;
  projected_event_count: number;
  last_projector_tick: Tick;
}

export interface SnapshotRequest {
  entity_id: UUID;
  at_ts: string; // ISO 8601
}

export interface PropertyHistoryPoint {
  timestamp: string;
  value: unknown;
  tick: Tick;
}

export interface PropertyHistory {
  entity_id: UUID;
  property_name: string;
  history: PropertyHistoryPoint[];
}

// -----------------------------------------------------------------------------
// Graph Types - PRP §5.2
// -----------------------------------------------------------------------------

export interface GraphNodePayload {
  node_id: string;
  label: string;
  type?: 'object_type' | 'entity' | 'action';
  properties?: Record<string, unknown>;
}

export interface GraphEdgePayload {
  edge_id: string;
  source_id: string;
  target_id: string;
  label: string;
  type?: 'link' | 'inheritance' | 'dependency';
}

export interface GraphSnapshotPayload {
  nodes: GraphNodePayload[];
  edges: GraphEdgePayload[];
}

export type ViewMode = 'story' | 'relation' | 'technical';

// -----------------------------------------------------------------------------
// Node Roles - PRP §5.2.1
// -----------------------------------------------------------------------------

export type NodeRole = 'hub' | 'active' | 'passive' | 'independent';

export interface NodeRoleBadge {
  role: NodeRole;
  label: string;
  color: string;
  icon: string;
}

export const NODE_ROLE_CONFIG: Record<NodeRole, NodeRoleBadge> = {
  hub: { role: 'hub', label: '枢纽', color: '#9b59b6', icon: '●' },
  active: { role: 'active', label: '主动', color: '#3498db', icon: '▲' },
  passive: { role: 'passive', label: '被动', color: '#e74c3c', icon: '▼' },
  independent: { role: 'independent', label: '独立', color: '#95a5a6', icon: '●' },
};

// -----------------------------------------------------------------------------
// Edge Label Translations - PRP §5.2.1
// -----------------------------------------------------------------------------

export type EdgeActionLabel =
  | 'attack' | 'engage' | 'support' | 'observe' | 'command' | 'control'
  | 'escort' | 'block' | 'scout' | 'repair' | 'supply' | 'defend'
  | 'link' | 'inherit' | 'depend';

export interface EdgeLabelTranslation {
  patterns: RegExp[];
  label: string;
}

export const EDGE_LABEL_TRANSLATIONS: EdgeLabelTranslation[] = [
  { patterns: [/attack/i, /engage/i, /打击/i], label: '正在攻击' },
  { patterns: [/command/i, /控制/i, /指挥/i], label: '正在指挥' },
  { patterns: [/support/i, /支援/i], label: '正在支援' },
  { patterns: [/observe/i, /侦查/i, /scan/i], label: '正在侦查' },
  { patterns: [/escort/i, /护航/i], label: '正在护航' },
  { patterns: [/block/i, /阻断/i], label: '正在阻断' },
  { patterns: [/scout/i, /侦察/i], label: '正在侦察' },
  { patterns: [/repair/i, /维修/i], label: '正在维修' },
  { patterns: [/supply/i, /补给/i], label: '正在补给' },
  { patterns: [/defend/i, /防御/i], label: '正在防御' },
  { patterns: [/link/i, /关联/i], label: '存在关联' },
  { patterns: [/inherit/i, /继承/i], label: '继承自' },
  { patterns: [/depend/i, /依赖/i], label: '依赖于' },
];

// -----------------------------------------------------------------------------
// Inspector Dynamic Forms - PRP §5.2
// -----------------------------------------------------------------------------

export type FieldType =
  | 'string'
  | 'integer'
  | 'float'
  | 'boolean'
  | 'coordinate'
  | 'entity_ref'
  | 'datetime'
  | 'enum'
  | 'soft_link'
  | 'derived'
  | 'time_series';

export interface InspectorFieldSchema {
  name: string;
  label: string;
  fieldType: FieldType;
  required?: boolean;
  readonly?: boolean;
  defaultValue?: unknown;
  options?: string[];
  min?: number;
  max?: number;
  pattern?: string;
  placeholder?: string;
  helpText?: string;
  validation?: {
    type: 'regex' | 'range' | 'enum' | 'custom';
    config: Record<string, unknown>;
  };
}

export interface InspectorObjectSchema {
  type_uri: string;
  display_name: string;
  fields: InspectorFieldSchema[];
  bound_actions: string[];
  access_level?: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'SECRET';
}

export interface InspectorState {
  editedValues: Record<string, unknown>;
  originalValues: Record<string, unknown>;
  validationErrors: Record<string, string>;
  isDirty: boolean;
  isValid: boolean;
}

// -----------------------------------------------------------------------------
// Timeline Enhancement - PRP §5.2, §6.4
// -----------------------------------------------------------------------------

export interface TickBufferConfig {
  maxSize: number;
  delta: number;
  circular: boolean;
}

export interface TimelineKeyframe {
  id: string;
  tick: Tick;
  label: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  isAuto: boolean;
}

export interface GhostFrame {
  tick: Tick;
  opacity: number;
  position?: { x: number; y: number; z?: number };
  properties?: Record<string, unknown>;
}

export interface TimelineState {
  currentTick: Tick;
  isPlaying: boolean;
  playbackSpeed: number;
  keyframes: TimelineKeyframe[];
  ghostFrames: GhostFrame[];
  bufferConfig: TickBufferConfig;
}

export interface PredictionFrame {
  tick: Tick;
  confidence: number;
  predictedBy: string;
  properties: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Copilot & AI - PRP §8
// -----------------------------------------------------------------------------

export type CopilotAgent = 'OAA' | 'LSA' | 'WFA' | 'DAA' | 'DBA' | 'Supervisor';

export interface CopilotRouteRequest {
  intent: string;
  prompt: string;
  context: {
    domain?: string;
    selected_nodes?: string[];
    current_view?: string;
    tick?: Tick;
  };
}

export interface CopilotRouteResponse {
  agent: CopilotAgent;
  confidence: number;
  guardrail: {
    allowed: boolean;
    reasons: string[];
    sanitized_prompt: string;
  };
  plan: string[];
  proposal?: ProposalSuggestion;
}

export interface CopilotContext {
  selectedNodes?: string[];
  currentView?: string;
  objectTypes?: string[];
  recentEvents?: string[];
  tick?: Tick;
  [key: string]: unknown;
}

// -----------------------------------------------------------------------------
// Proposal System - PRP §8.3
// -----------------------------------------------------------------------------

export type ProposalStatus = 'draft' | 'applied' | 'rejected' | 'rolled_back';

export interface ProposalPayload {
  proposal_id: string;
  title: string;
  intent: string;
  status: ProposalStatus;
  created_at: string;
  updated_at: string;
  code_changes?: CodeChange[];
  impact_analysis?: ImpactItem[];
  rollback_plan?: string[];
}

export interface CodeChange {
  file: string;
  type: 'add' | 'remove' | 'modify';
  line_start: number;
  line_end: number;
  old_code?: string;
  new_code?: string;
  description: string;
}

export interface ImpactItem {
  type: 'entity' | 'relationship' | 'action' | 'query';
  name: string;
  impact: 'high' | 'medium' | 'low';
  description: string;
  affected_count?: number;
}

// -----------------------------------------------------------------------------
// Lineage & Audit - PRP §5.2.1, §10.3
// -----------------------------------------------------------------------------

export interface LineageAggregate {
  lineage: {
    transaction: Record<string, unknown>;
    primary_event: Record<string, unknown> | null;
    compensation_event: Record<string, unknown> | null;
  };
  bus_events: Record<string, unknown>[];
}

export interface ComplianceRecord {
  action: string;
  subject_id: SubjectID;
  actor: SubjectID;
  recorded_at: string;
  details?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Service Adapter Types
// -----------------------------------------------------------------------------

export interface ServiceAdapterResponse {
  operation: string;
  status: 'ok' | 'error' | 'event_publish_failed';
  service: string;
  result: unknown;
}

export interface NotificationPayload {
  event_type?: string;
  created_at?: string;
  service?: string;
  correlation_id?: string;
  payload?: Record<string, unknown>;
}

export interface NotificationMessage {
  id: string;
  event_type: string;
  service: string;
  payload: Record<string, unknown>;
  correlation_id?: string;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Access Control - PRP §10.2
// -----------------------------------------------------------------------------

export interface AccessControl {
  read: string[];
  write: string[];
  delete: string[];
  admin?: string[];
}

export interface ABACDecision {
  allowed: boolean;
  denied_fields?: string[];
  reason?: string;
}

// -----------------------------------------------------------------------------
// Auth Types - PRP §10.1
// -----------------------------------------------------------------------------

export type UserRole = 'Admin' | 'Designer' | 'Operator' | 'Viewer';

export interface AuthUser {
  username: string;
  role: UserRole;
  permissions?: string[];
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  role: UserRole;
  expires_in?: number;
}

// -----------------------------------------------------------------------------
// Validation Types - PRP §7.1.2
// -----------------------------------------------------------------------------

export interface ValidationResponse {
  valid: boolean;
  errors: string[];
  hooks: {
    hook: string;
    passed: boolean;
    detail: string;
  }[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// -----------------------------------------------------------------------------
// Migration Types - PRP §3.3.2
// -----------------------------------------------------------------------------

export interface MigrationPlan {
  plan_id: string;
  source_version: string;
  target_version: string;
  steps: MigrationStep[];
  created_at: string;
}

export interface MigrationStep {
  order: number;
  type: 'add_field' | 'remove_field' | 'rename_field' | 'transform_field' | 'add_type' | 'remove_type';
  target: string;
  config: Record<string, unknown>;
}

export interface MigrationPlanRequest {
  source_version: string;
  target_version: string;
  changes: MigrationStep[];
}

// -----------------------------------------------------------------------------
// Telemetry Types - PRP §11.1
// -----------------------------------------------------------------------------

export interface TelemetryPoint {
  entity_id: UUID;
  property_name: string;
  value: unknown;
  timestamp: string;
  tick: Tick;
}

export interface TelemetrySummary {
  cpu_usage: number;
  memory_usage: number;
  active_entities: number;
  events_per_second: number;
  average_latency_ms: number;
}

// -----------------------------------------------------------------------------
// WebSocket Types
// -----------------------------------------------------------------------------

export interface WebSocketMessage {
  action: 'subscribe' | 'unsubscribe' | 'publish';
  channels?: string[];
  payload?: Record<string, unknown>;
}

export interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
}
