import {
  Alerta,
  Botao,
  CabecalhoPagina,
  CampoMensagem,
  CampoSelectMultiplo,
  Conversa,
  Mensagem,
  Referencias,
  Vazio,
} from '@celke/kole-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { usePolling } from '../hooks/usePolling';
import { ApiError, api, streamChat } from '../services/api';
import type { HistoryMessage, Source } from '../types/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  state: 'concluida' | 'gerando' | 'erro';
  sources?: Source[];
  /** O modelo está raciocinando antes de responder. */
  thinking?: boolean;
  error?: string;
  /** Pergunta que gerou esta resposta (para "Tentar novamente"). */
  question?: string;
  createdAt: Date;
}

const newId = () => crypto.randomUUID();

function toHistory(messages: ChatMessage[]): HistoryMessage[] {
  return messages
    .filter((m) => m.state === 'concluida' && m.content.trim())
    .map((m) => ({ role: m.role, content: m.content }));
}

export function ChatPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const documents = usePolling(api.chatDocuments, 0);
  const [selectedIds, setSelectedIds] = useState<string[]>(() => params.getAll('doc'));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const generating = messages.some((m) => m.state === 'gerando');

  // Documento escolhido pela URL que não existe mais (ou ainda não está pronto) sai da seleção.
  useEffect(() => {
    if (!documents.data) return;
    const valid = new Set(documents.data.map((d) => d.id));
    setSelectedIds((ids) => ids.filter((id) => valid.has(id)));
  }, [documents.data]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function patch(id: string, change: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) {
    setMessages((list) =>
      list.map((m) => (m.id === id ? { ...m, ...(typeof change === 'function' ? change(m) : change) } : m)),
    );
  }

  async function ask(question: string, history: HistoryMessage[], assistantId: string) {
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      for await (const event of streamChat({ question, document_ids: selectedIds, history }, controller.signal)) {
        if (event.type === 'sources') patch(assistantId, { sources: event.sources });
        else if (event.type === 'thinking') patch(assistantId, { thinking: true });
        else if (event.type === 'token') patch(assistantId, (m) => ({ content: m.content + event.text }));
        else if (event.type === 'error') {
          patch(assistantId, { state: 'erro', error: event.message });
          return;
        } else if (event.type === 'done') break;
      }
      patch(assistantId, (m) => ({
        state: 'concluida',
        content: m.content || (controller.signal.aborted ? 'Resposta interrompida.' : m.content),
      }));
    } catch (e) {
      if (controller.signal.aborted) {
        patch(assistantId, (m) => ({ state: 'concluida', content: m.content || 'Resposta interrompida.' }));
      } else {
        patch(assistantId, {
          state: 'erro',
          error: e instanceof ApiError ? e.message : 'Não foi possível obter a resposta.',
        });
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  function send(question: string) {
    if (!selectedIds.length || generating) return;
    const history = toHistory(messages);
    const assistantId = newId();
    const now = new Date();
    setMessages((list) => [
      ...list,
      { id: newId(), role: 'user', content: question, state: 'concluida', createdAt: now },
      { id: assistantId, role: 'assistant', content: '', state: 'gerando', question, createdAt: now },
    ]);
    setText('');
    void ask(question, history, assistantId);
  }

  function retry(message: ChatMessage) {
    if (!message.question || generating) return;
    const index = messages.findIndex((m) => m.id === message.id);
    const history = toHistory(messages.slice(0, Math.max(0, index - 1)));
    patch(message.id, { state: 'gerando', content: '', thinking: false, error: undefined, sources: undefined });
    void ask(message.question, history, message.id);
  }

  const options = (documents.data ?? []).map((d) => ({ valor: d.id, rotulo: d.filename }));
  const noDocuments = documents.data && documents.data.length === 0;

  return (
    <div className="app-chat">
      <CabecalhoPagina
        titulo="Chat"
        icone="message-square"
        acoes={
          <Botao
            rotulo="Nova conversa"
            icone="plus"
            severidade="secundario"
            disabled={!messages.length || generating}
            onClick={() => setMessages([])}
          />
        }
      />

      {documents.error && (
        <Alerta
          severidade="err"
          titulo="Não foi possível carregar os documentos"
          mensagem={documents.error.message}
          acoes={<Botao rotulo="Tentar de novo" tamanho="pequeno" onClick={documents.reload} />}
        />
      )}

      {noDocuments ? (
        <Vazio titulo="Nenhum documento pronto" descricao="Envie um PDF e aguarde o processamento para conversar sobre ele." icone="file-text">
          <Botao rotulo="Enviar PDF" icone="upload" onClick={() => navigate('/documentos')} />
        </Vazio>
      ) : (
        <>
          <CampoSelectMultiplo
            rotulo="Documentos da conversa"
            dica="As respostas usam só os trechos dos documentos escolhidos."
            placeholder={documents.loading ? 'Carregando…' : 'Escolha um ou mais documentos'}
            opcoes={options}
            valor={selectedIds}
            aoMudar={setSelectedIds}
            comBusca
            botaoLimpar
          />
          <div className="app-chat-conversa">
            <Conversa
              rotulo="Conversa com os documentos"
              larguraMaxima="52rem"
              vazio={
                <Vazio
                  titulo="Pergunte sobre seus documentos"
                  descricao="Escolha os documentos acima e escreva uma pergunta. A primeira resposta demora mais: o modelo é carregado na memória."
                  icone="bot"
                />
              }
              campo={
                <CampoMensagem
                  valor={text}
                  aoMudar={setText}
                  aoEnviar={send}
                  gerando={generating}
                  aoParar={() => abortRef.current?.abort()}
                  desabilitado={!selectedIds.length}
                  placeholder={selectedIds.length ? 'Escreva sua pergunta' : 'Escolha ao menos um documento'}
                  maxCaracteres={4000}
                />
              }
            >
              {messages.map((m) =>
                m.role === 'user' ? (
                  <Mensagem key={m.id} autor="usuario" nome="Você" hora={m.createdAt}>
                    {m.content}
                  </Mensagem>
                ) : (
                  <Mensagem
                    key={m.id}
                    autor="assistente"
                    nome="Celke IA"
                    avatar={<span className="app-avatar-ia" aria-hidden="true">IA</span>}
                    estado={m.state}
                    erro={m.error}
                    aoTentarNovamente={() => retry(m)}
                    copiavel
                    rodape={
                      m.sources?.length ? (
                        <Referencias
                          itens={m.sources.map((s, i) => ({
                            id: `${s.document_id}-${i}`,
                            titulo: `[${i + 1}] ${s.filename}`,
                            detalhe: `Página ${s.page}`,
                            trecho: s.excerpt,
                          }))}
                        />
                      ) : undefined
                    }
                  >
                    {m.content ||
                      (m.state === 'gerando' && m.thinking ? (
                        <span className="app-pensando">Analisando os trechos dos documentos…</span>
                      ) : undefined)}
                  </Mensagem>
                ),
              )}
            </Conversa>
          </div>
        </>
      )}
    </div>
  );
}
