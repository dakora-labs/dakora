import type { Template, RenderRequest, RenderResponse, HealthResponse } from '../types';

const API_BASE = '/api';

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

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(response);
  },

  async getPrompts(): Promise<string[]> {
    const response = await fetch(`${API_BASE}/templates`);
    return handleResponse<string[]>(response);
  },

  async getPrompt(id: string): Promise<Template> {
    const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`);
    return handleResponse<Template>(response);
  },

  async createPrompt(template: Omit<Template, 'inputs'> & {
    inputs: Record<string, { type: string; required: boolean; default?: unknown }>
  }): Promise<Template> {
    const response = await fetch(`${API_BASE}/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    });
    return handleResponse<Template>(response);
  },

  async updatePrompt(id: string, template: Partial<Omit<Template, 'id' | 'inputs'>> & {
    inputs?: Record<string, { type: string; required: boolean; default?: unknown }>
  }): Promise<Template> {
    const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    });
    return handleResponse<Template>(response);
  },

  async deletePrompt(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(errorData.detail || `HTTP ${response.status}`, response.status);
    }
  },

  async renderPrompt(id: string, request: RenderRequest): Promise<RenderResponse> {
    const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(id)}/render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    return handleResponse<RenderResponse>(response);
  },

  async getExamples(): Promise<Template[]> {
    const response = await fetch(`${API_BASE}/examples`);
    return handleResponse<Template[]>(response);
  },
};

export { ApiError };