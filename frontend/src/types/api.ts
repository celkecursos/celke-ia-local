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
  database: ServiceStatus;
  web_search: ServiceStatus;
}

export interface ChatDocument {
  id: string;
  filename: string;
  page_count: number | null;
}

export interface Source {
  kind?: 'document' | 'web';
  document_id?: string | null;
  /** Na web, é o título da página. */
  filename: string;
  page?: number | null;
  url?: string | null;
  excerpt: string;
  score?: number | null;
}

/** documents = veio dos PDFs; not_found = os PDFs não tinham a resposta; web = veio da busca na internet. */
export type AnswerKind = 'documents' | 'not_found' | 'web';

export interface ChatRequest {
  question: string;
  document_ids: string[];
  /** Sem conversa, o backend cria uma e avisa no evento `conversation`. */
  conversation_id?: string;
  /** Gera de novo a última resposta da conversa, que terminou em erro. */
  retry?: boolean;
  /** Responde com a busca na internet. Só a pergunta sai do computador. */
  web_search?: boolean;
}

export interface StoredMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  state: 'concluida' | 'erro';
  error_message: string | null;
  sources: Source[];
  answer_kind: AnswerKind;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: StoredMessage[];
}

/** Eventos do POST /api/chat (Server-Sent Events). */
export type ChatEvent =
  | { type: 'conversation'; id: string; title: string }
  | { type: 'searching' }
  | { type: 'sources'; sources: Source[] }
  | { type: 'thinking' }
  | { type: 'token'; text: string }
  | { type: 'not_found' }
  | { type: 'done' }
  | { type: 'error'; code: string; message: string };
