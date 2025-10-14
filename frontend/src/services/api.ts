/**
 * API service for communicating with the FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Export all interfaces
export interface TurnRecord {
  turn: number;
  timestamp: string;
  user_action?: string;
  narrative: string;
  state_changes: Array<{ op: string; path: string; value?: unknown }>;
  visible_dialogue?: Array<{ entity_id: string; utterance: string }>;
  roll_requests?: Array<{ kind: string; target?: string; difficulty?: number }>;
}

export interface Entity {
  id: string;
  type: string;
  name?: string;
  background?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any; // Allow additional properties
}

export interface Session {
  id: string;
  scenario_id: string;
  turn: number;
  status: string;
  state?: Record<string, unknown>;
  turn_history?: TurnRecord[];
  world_background?: string;
  entities?: Entity[];
  scenario_spec?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface SessionConfig {
  num_characters?: number;
  generate_world_background?: boolean;
  generate_entity_backgrounds?: boolean;
  initial_entities?: Entity[];
  custom_state?: Record<string, unknown>;
  player_name?: string;
}

export interface UserSettings {
  id: string;
  player_name: string;
  preferences: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface SettingsRequest {
  player_name: string;
  preferences?: Record<string, unknown>;
}

export interface SessionCreateRequest {
  scenario_id: string;
  seed?: number;
  config?: SessionConfig;
}

export interface TurnRequest {
  action?: string;
  parameters?: Record<string, unknown>;
}

export interface TurnResponse {
  session_id: string;
  turn: number;
  outcome: {
    narrative: string;
    visible_dialogue?: Array<{ entity_id: string; utterance: string }>;
    state_changes: Array<{ op: string; path: string; value?: unknown }>;
    roll_requests?: Array<{ kind: string; target?: string; difficulty?: number }>;
    suggested_actions?: string[];
  };
}

export interface ScenarioGenerateResponse {
  id: string;
  name: string;
  spec_version: string;
  status: string;
}

export interface ScenarioCompileResponse {
  id: string;
  status: string;
  validation_results: Record<string, unknown>;
}

export interface Memory {
  content: string;
  scope?: string;
  turn: number;
}

export interface MemoryData {
  private_memory: Record<string, Memory[]>;
  public_memory: Record<string, Memory[]>;
}

export interface RelationshipData {
  entity_a: string;
  entity_b: string;
  sentiment: number;
  relationship_type: string;
  memory_count: number;
  last_interaction: number;
}

export interface RelationshipsResponse {
  session_id: string;
  relationships: Record<string, RelationshipData>;
  entity_count: number;
  total_relationships: number;
}

export interface PromptEnrichRequest {
  description: string;
  max_tokens?: number;
}

export interface PromptEnrichResponse {
  original: string;
  enriched: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Session Management
  async createSession(request: SessionCreateRequest): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/sessions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    return response.json();
  }

  async getSession(sessionId: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.statusText}`);
    }

    return response.json();
  }

  async listSessions(): Promise<{ sessions: Session[] }> {
    const response = await fetch(`${this.baseUrl}/sessions/`);

    if (!response.ok) {
      throw new Error(`Failed to list sessions: ${response.statusText}`);
    }

    return response.json();
  }

  async processTurn(sessionId: string, request: TurnRequest): Promise<TurnResponse> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/turns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to process turn: ${response.statusText}`);
    }

    return response.json();
  }

  async *processTurnStreaming(sessionId: string, request: TurnRequest): AsyncIterableIterator<string> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/turns/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to process turn: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix

            if (data.trim() === '[DONE]') {
              return; // End of stream
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'narrative_chunk') {
                yield parsed.content;
              } else if (parsed.type === 'complete') {
                // Final outcome - we could yield this as well if needed
                return;
              }
            } catch {
              // Ignore malformed JSON lines
              console.warn('Failed to parse streaming data:', data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // Scenario Management
  async generateScenario(description: string): Promise<ScenarioGenerateResponse> {
    const response = await fetch(`${this.baseUrl}/scenarios/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ description }),
    });

    if (!response.ok) {
      throw new Error(`Failed to generate scenario: ${response.statusText}`);
    }

    return response.json();
  }

  async compileScenario(scenarioId: string): Promise<ScenarioCompileResponse> {
    const response = await fetch(`${this.baseUrl}/scenarios/${scenarioId}/compile`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to compile scenario: ${response.statusText}`);
    }

    return response.json();
  }

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Prompt Enrichment
  async enrichPrompt(description: string, maxTokens?: number): Promise<PromptEnrichResponse> {
    const response = await fetch(`${this.baseUrl}/prompts/enrich`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        description,
        max_tokens: maxTokens || 500
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to enrich prompt: ${response.statusText}`);
    }

    return response.json();
  }

  async getSessionMemories(sessionId: string): Promise<MemoryData> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/memories`);

    if (!response.ok) {
      throw new Error(`Failed to get session memories: ${response.statusText}`);
    }

    return response.json();
  }

  async getRelationships(sessionId: string): Promise<RelationshipsResponse> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/relationships`);

    if (!response.ok) {
      throw new Error(`Failed to get relationships: ${response.statusText}`);
    }

    return response.json();
  }

  // Settings Management
  async getUserSettings(): Promise<UserSettings> {
    const response = await fetch(`${this.baseUrl}/settings/`);

    if (!response.ok) {
      if (response.status === 404) {
        // Return default settings if none exist
        throw new Error('Settings not found');
      }
      throw new Error(`Failed to get user settings: ${response.statusText}`);
    }

    return response.json();
  }

  async saveUserSettings(request: SettingsRequest): Promise<UserSettings> {
    const response = await fetch(`${this.baseUrl}/settings/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to save user settings: ${response.statusText}`);
    }

    return response.json();
  }

  async updateUserSettings(request: SettingsRequest): Promise<UserSettings> {
    const response = await fetch(`${this.baseUrl}/settings/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to update user settings: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService();
