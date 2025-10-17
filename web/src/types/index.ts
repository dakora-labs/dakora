export interface Template {
  id: string;
  version: string;
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
  templates_loaded: number;
  vault_config: {
    registry_type: 'local' | 'azure';
    prompt_dir?: string;
    cloud_location?: string;
    logging_enabled: boolean;
  };
}

export interface ApiError {
  detail: string;
}