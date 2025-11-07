import type {
  Template,
  RenderRequest,
  RenderResponse,
  HealthResponse,
  PartListResponse,
  PromptPart,
  CreatePartRequest,
  UpdatePartRequest,
  ApiKeyListResponse,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKey,
  ModelsResponse,
  ExecutionRequest,
  ExecutionResponse,
  ExecutionHistoryResponse,
  ExecutionListResponse,
  ExecutionListFilters,
  ExecutionDetail,
  ExecutionDetailNew,
  ExecutionListItem,
  OptimizePromptRequest,
  OptimizePromptResponse,
  OptimizationRunsResponse,
  QuotaInfo, VersionHistoryResponse, RollbackRequest,
  RelatedTracesResponse,
  TraceHierarchy,
  FeedbackRequest,
  FeedbackResponse,
} from '../types';

interface UserContext {
  user_id: string;
  email: string;
  name: string | null;
  project_id: string;
  project_slug: string;
  project_name: string;
}

const getApiBase = () => {
  const apiUrl = import.meta.env.VITE_API_URL;
  return apiUrl ? `${apiUrl}/api` : '/api';
};

const API_BASE = getApiBase();

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
  }
  return response.json();
}

function buildQueryString(params: Record<string, unknown> | ExecutionListFilters): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') {
      continue;
    }

    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry !== undefined && entry !== null && entry !== '') {
          searchParams.append(key, String(entry));
        }
      });
      continue;
    }

    searchParams.append(key, String(value));
  }

  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

/**
 * Create API client with authentication support
 */
export function createApiClient(getToken?: () => Promise<string | null>) {
  async function getAuthHeaders(): Promise<HeadersInit> {
    if (!getToken) {
      return {};
    }

    const token = await getToken();
    if (token) {
      return {
        'Authorization': `Bearer ${token}`,
      };
    }

    return {};
  }

  return {
    async getUserContext(): Promise<UserContext> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/me/context`, {
        headers: authHeaders,
      });
      return handleResponse<UserContext>(response);
    },

    async getHealth(): Promise<HealthResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/health`, {
        headers: authHeaders,
      });
      return handleResponse<HealthResponse>(response);
    },

    async getProjectStats(projectId: string): Promise<{
      prompts_count: number;
      total_cost: number;
      total_executions: number;
      avg_cost_per_execution: number;
      daily_costs: Array<{ date: string; cost: number }>;
      top_prompts: Array<{ prompt_id: string; name: string; cost: number; execution_count: number }>;
    }> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/stats`, {
        headers: authHeaders,
      });
      return handleResponse<{
        prompts_count: number;
        total_cost: number;
        total_executions: number;
        avg_cost_per_execution: number;
        daily_costs: Array<{ date: string; cost: number }>;
        top_prompts: Array<{ prompt_id: string; name: string; cost: number; execution_count: number }>;
      }>(response);
    },

    async getPrompts(projectId: string): Promise<Template[]> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts`, {
        headers: authHeaders,
      });
      return handleResponse<Template[]>(response);
    },

    async getPrompt(projectId: string, id: string): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(id)}`, {
        headers: authHeaders,
      });
      return handleResponse<Template>(response);
    },

    async createPrompt(projectId: string, template: Omit<Template, 'inputs'> & {
      inputs: Record<string, { type: string; required: boolean; default?: unknown }>
    }): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(template),
      });
      return handleResponse<Template>(response);
    },

    async updatePrompt(projectId: string, id: string, template: Partial<Omit<Template, 'id' | 'inputs'>> & {
      inputs?: Record<string, { type: string; required: boolean; default?: unknown }>
    }): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(template),
      });
      return handleResponse<Template>(response);
    },

    async deletePrompt(projectId: string, id: string): Promise<void> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
      }
    },

    async renderPrompt(projectId: string, id: string, request: RenderRequest): Promise<RenderResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(id)}/render`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<RenderResponse>(response);
    },

    async getExamples(): Promise<Template[]> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/examples`, {
        headers: authHeaders,
      });
      return handleResponse<Template[]>(response);
    },

    async getPromptParts(projectId: string): Promise<PartListResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/parts`, {
        headers: authHeaders,
      });
      return handleResponse<PartListResponse>(response);
    },

    async getPromptPart(projectId: string, partId: string): Promise<PromptPart> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/parts/${encodeURIComponent(partId)}`, {
        headers: authHeaders,
      });
      return handleResponse<PromptPart>(response);
    },

    async createPromptPart(projectId: string, part: CreatePartRequest): Promise<PromptPart> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/parts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(part),
      });
      return handleResponse<PromptPart>(response);
    },

    async updatePromptPart(projectId: string, partId: string, part: UpdatePartRequest): Promise<PromptPart> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/parts/${encodeURIComponent(partId)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(part),
      });
      return handleResponse<PromptPart>(response);
    },

    async deletePromptPart(projectId: string, partId: string): Promise<void> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/parts/${encodeURIComponent(partId)}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
      }
    },

    async renderPreview(projectId: string, id: string): Promise<RenderResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(id)}/render`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          inputs: {},
          resolve_includes_only: true
        }),
      });
      return handleResponse<RenderResponse>(response);
    },

    async getApiKeys(projectId: string): Promise<ApiKeyListResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/api-keys`, {
        headers: authHeaders,
      });
      return handleResponse<ApiKeyListResponse>(response);
    },

    async createApiKey(projectId: string, request: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<ApiKeyCreateResponse>(response);
    },

    async getApiKey(projectId: string, keyId: string): Promise<ApiKey> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/api-keys/${encodeURIComponent(keyId)}`, {
        headers: authHeaders,
      });
      return handleResponse<ApiKey>(response);
    },

    async deleteApiKey(projectId: string, keyId: string): Promise<void> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/api-keys/${encodeURIComponent(keyId)}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
      }
    },

    async getModels(projectId: string): Promise<ModelsResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/models`, {
        headers: authHeaders,
      });
      return handleResponse<ModelsResponse>(response);
    },

    async getExecutions(projectId: string, filters: ExecutionListFilters = {}): Promise<ExecutionListResponse> {
      const authHeaders = await getAuthHeaders();
      const query = buildQueryString(filters);
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/executions${query}`, {
        headers: authHeaders,
      });

      const data = await handleResponse<unknown>(response);

      const toExecutionListItem = (entry: any): ExecutionListItem => {
        const traceIdRaw = entry?.trace_id ?? entry?.traceId ?? '';
        const traceId = typeof traceIdRaw === 'string' ? traceIdRaw : String(traceIdRaw ?? '');

        const createdAtRaw = entry?.created_at ?? entry?.createdAt ?? null;
        const createdAt =
          typeof createdAtRaw === 'string'
            ? createdAtRaw
            : createdAtRaw instanceof Date
              ? createdAtRaw.toISOString()
              : createdAtRaw ? new Date(createdAtRaw).toISOString() : null;

        const tokensIn = entry?.tokens_in ?? entry?.tokensIn ?? null;
        const tokensOut = entry?.tokens_out ?? entry?.tokensOut ?? null;
        const totalTokensIn = entry?.total_tokens_in ?? entry?.totalTokensIn ?? null;
        const totalTokensOut = entry?.total_tokens_out ?? entry?.totalTokensOut ?? null;
        const latencyMs = entry?.latency_ms ?? entry?.latencyMs ?? null;
        const costUsd = entry?.cost_usd ?? entry?.costUsd ?? null;
        const templateCountSource =
          entry?.template_count ??
          entry?.templateCount ??
          (Array.isArray(entry?.template_usages) ? entry.template_usages.length : undefined);
        let templateCount = 0;
        if (typeof templateCountSource === 'number' && Number.isFinite(templateCountSource)) {
          templateCount = templateCountSource;
        } else if (templateCountSource !== undefined && templateCountSource !== null) {
          const numeric = Number(templateCountSource);
          if (Number.isFinite(numeric)) {
            templateCount = numeric;
          }
        }

        return {
          traceId,
          createdAt,
          provider: entry?.provider ?? null,
          model: entry?.model ?? null,
          tokensIn,
          tokensOut,
          totalTokensIn,
          totalTokensOut,
          latencyMs,
          costUsd,
          sessionId: entry?.session_id ?? entry?.sessionId ?? undefined,
          agentId: entry?.agent_id ?? entry?.agentId ?? undefined,
          parentTraceId: entry?.parent_trace_id ?? entry?.parentTraceId ?? undefined,
          templateCount,
          // Priority 1 UI improvements
          spanCount: entry?.span_count ?? entry?.spanCount ?? 0,
          spanTypeBreakdown: entry?.span_type_breakdown ?? entry?.spanTypeBreakdown ?? undefined,
          hasErrors: entry?.has_errors ?? entry?.hasErrors ?? false,
          errorMessage: entry?.error_message ?? entry?.errorMessage ?? null,
          // Multi-agent/model detection
          uniqueAgents: entry?.unique_agents ?? entry?.uniqueAgents ?? undefined,
          uniqueModels: entry?.unique_models ?? entry?.uniqueModels ?? undefined,
        };
      };

      if (Array.isArray(data)) {
        const normalized = data.map(toExecutionListItem);
        return {
          executions: normalized,
          total: normalized.length + (filters.offset ?? 0),
          limit: filters.limit ?? normalized.length,
          offset: filters.offset ?? 0,
        };
      }

      if (data && typeof data === 'object') {
        const executionsRaw = Array.isArray((data as any).executions) ? (data as any).executions : [];
        const normalized = executionsRaw.map(toExecutionListItem);
        return {
          executions: normalized,
          total: typeof (data as any).total === 'number'
            ? (data as any).total
            : normalized.length + (filters.offset ?? 0),
          limit: typeof (data as any).limit === 'number'
            ? (data as any).limit
            : filters.limit ?? normalized.length,
          offset: typeof (data as any).offset === 'number'
            ? (data as any).offset
            : filters.offset ?? 0,
        };
      }

      return {
        executions: [],
        total: 0,
        limit: filters.limit ?? 0,
        offset: filters.offset ?? 0,
      };
    },

    async getExecution(projectId: string, traceId: string, spanId?: string): Promise<ExecutionDetail | ExecutionDetailNew> {
      const authHeaders = await getAuthHeaders();
      const url = spanId 
        ? `${API_BASE}/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(traceId)}?span_id=${encodeURIComponent(spanId)}`
        : `${API_BASE}/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(traceId)}`;
      
      const response = await fetch(url, {
        headers: authHeaders,
      });

      const data = await handleResponse<any>(response);

      // Check if this is the new schema response (has input_messages/output_messages)
      if (data?.input_messages || data?.output_messages) {
        // NEW SCHEMA - Return ExecutionDetailNew
        return {
          trace_id: data.trace_id ?? traceId,
          span_id: data.span_id ?? '',
          type: data.type ?? 'unknown',
          agent_name: data.agent_name ?? null,
          provider: data.provider ?? null,
          model: data.model ?? null,
          start_time: data.start_time ?? data.created_at ?? new Date().toISOString(),
          end_time: data.end_time ?? new Date().toISOString(),
          latency_ms: data.latency_ms ?? null,
          tokens_in: data.tokens_in ?? null,
          tokens_out: data.tokens_out ?? null,
          total_cost_usd: data.total_cost_usd ?? null,
          status: data.status ?? null,
          status_message: data.status_message ?? null,
          attributes: data.attributes ?? null,
          input_messages: Array.isArray(data.input_messages) ? data.input_messages : [],
          output_messages: Array.isArray(data.output_messages) ? data.output_messages : [],
          child_spans: Array.isArray(data.child_spans) ? data.child_spans : [],
          template_usages: Array.isArray(data.template_usages) ? data.template_usages : [],
          template_info: data.template_info ?? null,
          created_at: data.created_at ?? data.start_time ?? new Date().toISOString(),
        } as ExecutionDetailNew;
      }

      // OLD SCHEMA - Return ExecutionDetail (existing logic)
      const normalizeNumber = (value: unknown): number | null => {
        if (typeof value === 'number' && Number.isFinite(value)) {
          return value;
        }
        if (value === null || value === undefined) {
          return null;
        }
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
      };

      const resolvedTraceIdRaw = data?.trace_id ?? data?.traceId ?? traceId;
      const resolvedTraceId: string =
        typeof resolvedTraceIdRaw === 'string'
          ? resolvedTraceIdRaw
          : String(resolvedTraceIdRaw ?? traceId ?? '');
      const createdAtRaw = data?.created_at ?? data?.createdAt ?? null;
      const createdAt =
        typeof createdAtRaw === 'string'
          ? createdAtRaw
          : createdAtRaw instanceof Date
            ? createdAtRaw.toISOString()
            : createdAtRaw
              ? new Date(createdAtRaw).toISOString()
              : null;

      const tokensIn = normalizeNumber(data?.tokens_in ?? data?.tokens?.in);
      const tokensOut = normalizeNumber(data?.tokens_out ?? data?.tokens?.out);
      const tokensTotalRaw = normalizeNumber(data?.tokens_total ?? data?.tokens?.total);
      const tokensTotal =
        tokensTotalRaw ??
        (tokensIn !== null || tokensOut !== null
          ? (tokensIn ?? 0) + (tokensOut ?? 0)
          : null);

      const parseJsonIfString = <T>(value: unknown): T | null => {
        if (value === null || value === undefined) {
          return null;
        }
        if (typeof value === 'object') {
          return value as T;
        }
        if (typeof value === 'string') {
          try {
            return JSON.parse(value) as T;
          } catch {
            return null;
          }
        }
        return null;
      };

      const conversationRaw =
        data?.conversation_history ??
        data?.conversationHistory ??
        parseJsonIfString<any[]>(data?.conversation_history_json) ??
        [];
      const conversationHistory = Array.isArray(conversationRaw)
        ? conversationRaw
            .filter((entry) => entry && typeof entry === 'object')
            .map((entry) => ({
              role: entry.role ?? entry?.speaker ?? 'assistant',
              content: (() => {
                const contentRaw = entry.content ?? entry?.message ?? '';
                if (typeof contentRaw === 'string') {
                  return contentRaw;
                }
                try {
                  return JSON.stringify(contentRaw, null, 2);
                } catch {
                  return String(contentRaw);
                }
              })(),
              name: entry.name ?? null,
              timestamp: entry.timestamp ?? entry.time ?? null,
              metadata: entry.metadata ?? null,
            }))
        : [];

      const templateUsagesRaw =
        data?.template_usages ??
        data?.templates_used ??
        data?.templateUsages ??
        [];

      const templateUsages = Array.isArray(templateUsagesRaw)
        ? templateUsagesRaw
            .filter((item) => item && typeof item === 'object')
            .map((item, index) => ({
              prompt_id: item.prompt_id ?? item.promptId ?? '',
              version: item.version ?? item.template_version ?? '',
              inputs: (() => {
                const raw = item.inputs ?? item.inputs_json ?? null;
                if (raw === null || raw === undefined) {
                  return null;
                }
                if (typeof raw === 'object') {
                  return raw;
                }
                if (typeof raw === 'string') {
                  try {
                    return JSON.parse(raw);
                  } catch {
                    return { value: raw };
                  }
                }
                return raw;
              })(),
              position:
                typeof item.position === 'number'
                  ? item.position
                  : Number.isFinite(Number(item.position))
                    ? Number(item.position)
                    : index,
              rendered_prompt: item.rendered_prompt ?? item.renderedPrompt ?? undefined,
            }))
        : [];

      const metadataParsed = parseJsonIfString<Record<string, unknown>>(data?.metadata);
      const metadata =
        metadataParsed ??
        (data?.metadata && typeof data.metadata === 'object' ? data.metadata : null);

      return {
        traceId: resolvedTraceId,
        createdAt,
        conversationHistory,
        metadata,
        provider: data?.provider ?? null,
        model: data?.model ?? null,
        tokens: {
          in: tokensIn ?? null,
          out: tokensOut ?? null,
          total: tokensTotal,
        },
        costUsd: normalizeNumber(data?.cost_usd ?? data?.costUsd),
        latencyMs: normalizeNumber(data?.latency_ms ?? data?.latencyMs),
        sessionId: data?.session_id ?? data?.sessionId ?? null,
        agentId: data?.agent_id ?? data?.agentId ?? null,
        parentTraceId: data?.parent_trace_id ?? data?.parentTraceId ?? null,
        templateUsages,
      };
    },

    async getRelatedTraces(projectId: string, traceId: string): Promise<RelatedTracesResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(traceId)}/related`, {
        headers: authHeaders,
      });
      return handleResponse<RelatedTracesResponse>(response);
    },

    async getExecutionHierarchy(projectId: string, traceId: string): Promise<TraceHierarchy> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(traceId)}/hierarchy`, {
        headers: authHeaders,
      });
      return handleResponse<TraceHierarchy>(response);
    },

    async executePrompt(projectId: string, promptId: string, request: ExecutionRequest): Promise<ExecutionResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<ExecutionResponse>(response);
    },

    async getExecutionHistory(projectId: string, promptId: string): Promise<ExecutionHistoryResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/executions`, {
        headers: authHeaders,
      });
      return handleResponse<ExecutionHistoryResponse>(response);
    },

    async optimizePrompt(projectId: string, promptId: string, request: OptimizePromptRequest): Promise<OptimizePromptResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<OptimizePromptResponse>(response);
    },

    async getQuotaInfo(workspaceId: string): Promise<QuotaInfo> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/workspaces/${encodeURIComponent(workspaceId)}/quota`, {
        headers: authHeaders,
      });
      return handleResponse<QuotaInfo>(response);
    },

    async getOptimizationRuns(projectId: string, promptId: string): Promise<OptimizationRunsResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/optimization-runs`, {
        headers: authHeaders,
      });
      return handleResponse<OptimizationRunsResponse>(response);
    },

    async getVersionHistory(projectId: string, promptId: string): Promise<VersionHistoryResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/versions`, {
        headers: authHeaders,
      });
      return handleResponse<VersionHistoryResponse>(response);
    },

    async getPromptVersion(projectId: string, promptId: string, version: number): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/versions/${version}`, {
        headers: authHeaders,
      });
      return handleResponse<Template>(response);
    },

    async rollbackPrompt(projectId: string, promptId: string, request: RollbackRequest): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(promptId)}/rollback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<Template>(response);
    },

    async getBudget(projectId: string): Promise<{
      exceeded: boolean;
      budget_usd: number | null;
      current_spend_usd: number;
      percentage_used: number;
      alert_threshold_pct: number;
      enforcement_mode: string;
      status: 'unlimited' | 'ok' | 'warning' | 'exceeded';
    }> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/budget`, {
        headers: authHeaders,
      });
      return handleResponse(response);
    },

    async updateBudget(
      projectId: string,
      request: {
        budget_monthly_usd?: number | null;
        alert_threshold_pct?: number;
        enforcement_mode?: string;
      }
    ): Promise<{
      exceeded: boolean;
      budget_usd: number | null;
      current_spend_usd: number;
      percentage_used: number;
      alert_threshold_pct: number;
      enforcement_mode: string;
      status: 'unlimited' | 'ok' | 'warning' | 'exceeded';
    }> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/budget`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse(response);
    },

    async submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(request),
      });
      return handleResponse<FeedbackResponse>(response);
    },
  };
}

// Default API client without authentication (for backwards compatibility)
export const api = createApiClient();

export { ApiError };
export type { UserContext };
