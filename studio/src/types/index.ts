export interface Prompt {
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