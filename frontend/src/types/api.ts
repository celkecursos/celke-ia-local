export type DocumentStatus = 'pendente' | 'processando' | 'pronto' | 'erro';

export interface DocumentItem {
  id: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  page_count: number | null;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  embedding_model: string | null;
  created_at: string;
  updated_at: string;
  needs_reindex: boolean;
}

export interface DocumentStats {
  total: number;
  ready: number;
  processing: number;
  error: number;
}

export interface ModelStatus {
  name: string;
  installed: boolean;
}

export interface ServiceStatus {
  online: boolean;
  error: string | null;
}

export interface SystemStatus {
  backend: ServiceStatus;
  ollama: {
    online: boolean;
    chat_model: ModelStatus;
    embedding_model: ModelStatus;
    error: string | null;
  };
  vector_store: ServiceStatus;
}

export interface ChatDocument {
  id: string;
  filename: string;
  page_count: number | null;
}

export interface Source {
  document_id: string;
  filename: string;
  page: number;
  excerpt: string;
  score: number;
}

export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  question: string;
  document_ids: string[];
  history: HistoryMessage[];
}

/** Eventos do POST /api/chat (Server-Sent Events). */
export type ChatEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'thinking' }
  | { type: 'token'; text: string }
  | { type: 'done' }
  | { type: 'error'; code: string; message: string };
