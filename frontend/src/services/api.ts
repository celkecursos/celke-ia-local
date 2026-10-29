import type {
  ChatDocument,
  ChatEvent,
  ChatRequest,
  DocumentItem,
  DocumentStats,
  SystemStatus,
} from '../types/api';
import { readSse } from './sse';

/** Base da API. Vazio = mesma origem (o nginx ou o Vite repassam /api ao backend). */
const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '') + '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = 'erro',
  ) {
    super(message);
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    if (body?.erro?.mensagem) return new ApiError(body.erro.mensagem, response.status, body.erro.codigo);
  } catch {
    // resposta sem JSON (proxy, timeout…)
  }
  if (response.status === 502 || response.status === 504) {
    return new ApiError('O backend não respondeu. Verifique se os containers estão rodando.', response.status);
  }
  return new ApiError(`Erro ${response.status} ao acessar a API.`, response.status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_URL + path, init);
  } catch {
    throw new ApiError('Não foi possível conectar ao backend.', 0, 'sem_conexao');
  }
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  status: () => request<SystemStatus>('/status'),
  stats: () => request<DocumentStats>('/documents/stats'),
  documents: () => request<{ items: DocumentItem[] }>('/documents').then((r) => r.items),
  document: (id: string) => request<DocumentItem>(`/documents/${encodeURIComponent(id)}`),
  deleteDocument: (id: string) => request<void>(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  reprocess: (id: string) =>
    request<DocumentItem>(`/documents/${encodeURIComponent(id)}/reprocess`, { method: 'POST' }),
  chatDocuments: () => request<{ items: ChatDocument[] }>('/chat/documents').then((r) => r.items),
};

/**
 * Envia o PDF com XMLHttpRequest: o `fetch` não informa o progresso do envio.
 */
export function uploadDocument(file: File, onProgress: (percent: number) => void): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}/documents`);
    xhr.responseType = 'json';
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) return resolve(xhr.response as DocumentItem);
      const body = xhr.response;
      if (xhr.status === 413 && !body?.erro) {
        return reject(new ApiError('O arquivo passa do limite de tamanho do servidor.', 413));
      }
      reject(new ApiError(body?.erro?.mensagem ?? `Erro ${xhr.status} no envio.`, xhr.status, body?.erro?.codigo));
    };
    xhr.onerror = () => reject(new ApiError('Não foi possível conectar ao backend.', 0, 'sem_conexao'));
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

/** Pergunta ao backend e devolve os eventos do streaming conforme chegam. */
export async function* streamChat(body: ChatRequest, signal: AbortSignal): AsyncGenerator<ChatEvent> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if (signal.aborted) return;
    throw e instanceof Error && e.name === 'AbortError'
      ? e
      : new ApiError('Não foi possível conectar ao backend.', 0, 'sem_conexao');
  }
  if (!response.ok || !response.body) throw await errorFrom(response);
  yield* readSse(response.body);
}
