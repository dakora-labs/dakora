import type { Template, RenderRequest, RenderResponse, HealthResponse, PartListResponse, PromptPart, CreatePartRequest, UpdatePartRequest, ApiKeyListResponse, ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKey } from '../types';

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

    async getPrompts(projectId: string): Promise<string[]> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/prompts`, {
        headers: authHeaders,
      });
      return handleResponse<string[]>(response);
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
  };
}

// Default API client without authentication (for backwards compatibility)
export const api = createApiClient();

export { ApiError };
export type { UserContext };