export interface Prompt {
  id: string;
  version: string;
  version_number?: number | null;
  description?: string;
  template: string;
  inputs: Record<string, InputSpec>;
  metadata?: Record<string, unknown>;
}

export interface InputSpec {
  type: 'string' | 'number' | 'boolean' | 'array<string>' | 'object';
  required: boolean;
  default?: unknown;
}

export interface RenderRequest {
  inputs: Record<string, unknown>;
}

export interface RenderResponse {
  rendered: string;
  inputs_used: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  prompts_count: number;
  vault_config: {
    registry_type: 'local' | 'azure';
    prompt_dir?: string;
    cloud_location?: string;
    logging_enabled: boolean;
  };
}

export type Template = Prompt;

export interface ApiError {
  detail: string;
}

export interface PromptPart {
  id: string;
  part_id: string;
  category: string;
  name: string;
  description?: string;
  content: string;
  tags: string[];
  version?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PartListResponse {
  by_category: Record<string, PromptPart[]>;
}

export interface CreatePartRequest {
  part_id: string;
  category: string;
  name: string;
  content: string;
  description?: string;
  tags?: string[];
  version?: string;
}

export interface UpdatePartRequest {
  category?: string;
  name?: string;
  content?: string;
  description?: string;
  tags?: string[];
  version?: string;
}

export interface ApiKey {
  id: string;
  name: string | null;
  key_preview: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface ApiKeyCreateRequest {
  name?: string | null;
  expires_in_days?: number | null;
}

export interface ApiKeyCreateResponse {
  id: string;
  name: string | null;
  key: string;
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
}

export interface ApiKeyListResponse {
  keys: ApiKey[];
  count: number;
  limit: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  max_tokens: number;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default_model: string;
}

export interface ExecutionMetrics {
  tokens_input: number;
  tokens_output: number;
  tokens_total: number;
  cost_usd: number;
  latency_ms: number;
}

export interface ExecutionRequest {
  inputs: Record<string, unknown>;
  model?: string;
  provider?: string;
}

export interface ExecutionResponse {
  execution_id: string;
  trace_id?: string | null;
  content: string;
  metrics: ExecutionMetrics;
  model: string;
  provider: string;
  created_at: string;
}

export interface ExecutionHistoryItem {
  execution_id: string;
  prompt_id: string;
  version: string;
  trace_id?: string | null;
  inputs: Record<string, unknown>;
  model: string;
  provider: string;
  output_text: string | null;
  error_message: string | null;
  status: 'success' | 'error' | 'quota_exceeded';
  metrics: ExecutionMetrics | null;
  created_at: string;
}

export interface ExecutionHistoryResponse {
  executions: ExecutionHistoryItem[];
  total: number;
}

export interface ExecutionListFilters {
  session_id?: string | null;
  agent_id?: string | null;
  provider?: string | null;
  model?: string | null;
  prompt_id?: string | null;
  has_templates?: boolean;
  min_cost?: number;
  start?: string;
  end?: string;
  page?: number;
  page_size?: number;
  limit?: number;
  offset?: number;
}

export interface ExecutionListItem {
  traceId: string;
  createdAt: string | null;
  provider: string | null;
  model: string | null;
  tokensIn: number | null;
  tokensOut: number | null;
  latencyMs: number | null;
  costUsd: number | null;
  sessionId?: string | null;
  agentId?: string | null;
  parentTraceId?: string | null;
  templateCount: number;
}

export interface ExecutionListResponse {
  executions: ExecutionListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConversationMessage {
  role: string;
  content: string;
  name?: string | null;
  timestamp?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface TemplateUsageEntry {
  traceId: string;
  promptId: string;
  version: string;
  inputs: Record<string, unknown> | null;
  position: number;
  renderedPrompt?: string;
}

export interface ExecutionDetail {
  traceId: string;
  createdAt: string | null;
  conversationHistory: ConversationMessage[];
  metadata: Record<string, unknown> | null;
  provider: string | null;
  model: string | null;
  tokens: {
    in: number | null;
    out: number | null;
    total: number | null;
  };
  costUsd: number | null;
  latencyMs: number | null;
  sessionId?: string | null;
  agentId?: string | null;
  parentTraceId?: string | null;
  templateUsages: TemplateUsageEntry[];
}

export interface RelatedTraceInfo {
  trace_id: string;
  agent_id: string | null;
  created_at: string | null;
  latency_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
}

export interface SessionAgentInfo {
  agent_id: string;
  trace_count: number;
}

export interface RelatedTracesResponse {
  trace_id: string;
  parent: RelatedTraceInfo | null;
  children: RelatedTraceInfo[];
  siblings: RelatedTraceInfo[];
  session_agents: SessionAgentInfo[];
}

export interface OptimizationInsight {
  category: string;
  description: string;
  impact: string;
}

export interface OptimizePromptRequest {
  test_cases?: Record<string, unknown>[] | null;
}

export interface OptimizePromptResponse {
  optimization_id: string;
  original_template: string;
  optimized_template: string;
  insights: OptimizationInsight[];
  token_reduction_pct: number;
  created_at: string;
}

export interface OptimizationRunRecord {
  optimization_id: string;
  prompt_id: string;
  version: string;
  original_template: string;
  optimized_template: string;
  insights: OptimizationInsight[];
  token_reduction_pct: number;
  applied: boolean;
  created_at: string;
}

export interface OptimizationRunsResponse {
  optimization_runs: OptimizationRunRecord[];
  total: number;
}

export interface QuotaInfo {
  optimizations_used: number;
  optimizations_limit: number;
  optimizations_remaining: number;
  usage_percentage: number;
  period_start: string;
  period_end: string;
}
export interface OptimizationInsight {
  category: string;
  description: string;
  impact: string;
}

export interface OptimizePromptRequest {
  test_cases?: Record<string, unknown>[] | null;
}

export interface OptimizePromptResponse {
  optimization_id: string;
  original_template: string;
  optimized_template: string;
  insights: OptimizationInsight[];
  token_reduction_pct: number;
  created_at: string;
}

export interface OptimizationRunRecord {
  optimization_id: string;
  prompt_id: string;
  version: string;
  original_template: string;
  optimized_template: string;
  insights: OptimizationInsight[];
  token_reduction_pct: number;
  applied: boolean;
  created_at: string;
}

export interface OptimizationRunsResponse {
  optimization_runs: OptimizationRunRecord[];
  total: number;
}

export interface QuotaInfo {
  optimizations_used: number;
  optimizations_limit: number;
  optimizations_remaining: number;
  usage_percentage: number;
  period_start: string;
  period_end: string;
}

export interface VersionHistoryItem {
  version: number;
  content_hash: string;
  created_at: string;
  created_by: string | null;
  metadata: Record<string, unknown> | null;
}

export interface VersionHistoryResponse {
  versions: VersionHistoryItem[];
  total: number;
}

export interface RollbackRequest {
  version: number;
}

export interface FeedbackRequest {
  rating: number;
  feedback?: string;
}

export interface FeedbackResponse {
  id: string;
  created_at: string;
}
