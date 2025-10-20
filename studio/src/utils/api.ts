import type { Template, RenderRequest, RenderResponse, HealthResponse } from '../types';

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
    async getHealth(): Promise<HealthResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/health`, {
        headers: authHeaders,
      });
      return handleResponse<HealthResponse>(response);
    },

    async getPrompts(): Promise<string[]> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates`, {
        headers: authHeaders,
      });
      return handleResponse<string[]>(response);
    },

    async getPrompt(id: string): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`, {
        headers: authHeaders,
      });
      return handleResponse<Template>(response);
    },

    async createPrompt(template: Omit<Template, 'inputs'> & {
      inputs: Record<string, { type: string; required: boolean; default?: unknown }>
    }): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(template),
      });
      return handleResponse<Template>(response);
    },

    async updatePrompt(id: string, template: Partial<Omit<Template, 'id' | 'inputs'>> & {
      inputs?: Record<string, { type: string; required: boolean; default?: unknown }>
    }): Promise<Template> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(template),
      });
      return handleResponse<Template>(response);
    },

    async deletePrompt(id: string): Promise<void> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
      }
    },

    async renderPrompt(id: string, request: RenderRequest): Promise<RenderResponse> {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}/render`, {
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
  };
}

// Default API client without authentication (for backwards compatibility)
export const api = createApiClient();

export { ApiError };