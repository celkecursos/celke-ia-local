import {
  Alerta,
  Botao,
  CabecalhoPagina,
  CampoMensagem,
  CampoSelectMultiplo,
  Conversa,
  Chip,
  Dialogo,
  ItemLista,
  Lista,
  MenuSuspenso,
  Mensagem,
  Referencias,
  Vazio,
  formatDataHoraBr,
  useConfirmacao,
  useToast,
} from '@celke/kole-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { usePolling } from '../hooks/usePolling';
import { ApiError, api, streamChat } from '../services/api';
import type { AnswerKind, Source, StoredMessage } from '../types/api';

const WEB_SEARCH_NOTICE = 'Só a pergunta é enviada ao buscador. Os seus PDFs continuam no computador.';

function hostOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function toReference(s: Source, i: number) {
  const base = { id: `${s.document_id ?? s.url}-${i}`, titulo: `[${i + 1}] ${s.filename}`, trecho: s.excerpt };
  return s.kind === 'web' && s.url
    ? { ...base, detalhe: hostOf(s.url), href: s.url }
    : { ...base, detalhe: `Página ${s.page}` };
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  state: 'concluida' | 'gerando' | 'erro';
  sources?: Source[];
  /** O modelo está raciocinando antes de responder. */
  thinking?: boolean;
  /** A busca na internet está em andamento. */
  searching?: boolean;
  answerKind?: AnswerKind;
  error?: string;
  createdAt: Date;
}

const newId = () => crypto.randomUUID();

function fromStored(m: StoredMessage): ChatMessage {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    state: m.state,
    sources: m.sources,
    answerKind: m.answer_kind,
    error: m.error_message ?? undefined,
    createdAt: new Date(m.created_at),
  };
}

export function ChatPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const confirmar = useConfirmacao();
  const [params, setParams] = useSearchParams();
  const conversationParam = params.get('conversa');
  const documents = usePolling(api.chatDocuments, 0);
  const conversations = usePolling(api.conversations, 0);
  const [selectedIds, setSelectedIds] = useState<string[]>(() => params.getAll('doc'));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  // Começa em Documentos: nada vai para a internet sem a pessoa escolher.
  const [answerFrom, setAnswerFrom] = useState<'documents' | 'web'>('documents');
  const [listOpen, setListOpen] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [loadError, setLoadError] = useState<string>();
  const abortRef = useRef<AbortController | null>(null);
  // Conversa cujas mensagens estão na tela (a da URL, depois de carregada).
  const currentRef = useRef<string | null>(null);
  const generating = messages.some((m) => m.state === 'gerando');
  const current = conversations.data?.find((c) => c.id === conversationParam);

  // Documento escolhido que não existe mais (ou ainda não está pronto) sai da seleção.
  useEffect(() => {
    if (!documents.data) return;
    const valid = new Set(documents.data.map((d) => d.id));
    if (selectedIds.every((id) => valid.has(id))) return;
    setSelectedIds((ids) => ids.filter((id) => valid.has(id)));
  }, [documents.data, selectedIds]);

  // A conversa da URL: abre ao recarregar a página ou ao escolher na lista.
  useEffect(() => {
    if (conversationParam === currentRef.current) return;
    abortRef.current?.abort();
    currentRef.current = conversationParam;
    setLoadError(undefined);
    setAnswerFrom('documents');
    if (!conversationParam) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingConversation(true);
    setMessages([]);
    // Conversa aberta começa sem documentos: a pessoa escolhe os da próxima pergunta.
    setSelectedIds([]);
    api
      .conversation(conversationParam)
      .then((c) => {
        if (cancelled) return;
        setMessages(c.messages.map(fromStored));
      })
      .catch((e) => {
        if (cancelled) return;
        currentRef.current = null;
        setLoadError(e instanceof ApiError ? e.message : 'Não foi possível abrir a conversa.');
      })
      .finally(() => {
        if (!cancelled) setLoadingConversation(false);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationParam]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function patch(id: string, change: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) {
    setMessages((list) =>
      list.map((m) => (m.id === id ? { ...m, ...(typeof change === 'function' ? change(m) : change) } : m)),
    );
  }

  async function ask(question: string, assistantId: string, retry = false, webSearch = false) {
    const controller = new AbortController();
    abortRef.current = controller;
    const body = {
      question,
      document_ids: selectedIds,
      conversation_id: currentRef.current ?? undefined,
      retry,
      web_search: webSearch,
    };
    try {
      for await (const event of streamChat(body, controller.signal)) {
        if (controller.signal.aborted) break;
        if (event.type === 'conversation') {
          if (currentRef.current !== event.id) {
            // A conversa nova vai para a URL: recarregar a página continua nela.
            currentRef.current = event.id;
            setParams({ conversa: event.id }, { replace: true });
          }
        } else if (event.type === 'searching') patch(assistantId, { searching: true });
        else if (event.type === 'sources') patch(assistantId, { sources: event.sources, searching: false });
        else if (event.type === 'not_found') patch(assistantId, { answerKind: 'not_found' });
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
      void conversations.reload();
    }
  }

  function send(question: string, webSearch = false) {
    if ((!webSearch && !selectedIds.length) || generating) return;
    const assistantId = newId();
    const now = new Date();
    setMessages((list) => [
      ...list,
      { id: newId(), role: 'user', content: question, state: 'concluida', createdAt: now },
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        state: 'gerando',
        answerKind: webSearch ? 'web' : 'documents',
        createdAt: now,
      },
    ]);
    void ask(question, assistantId, false, webSearch);
  }

  /** A pessoa pediu: repete a pergunta da resposta na busca na internet. */
  function searchWeb(index: number) {
    const question = messages[index - 1]?.content;
    if (question) send(question, true);
  }

  /** Só a última resposta, que deu erro: o backend refaz a mesma pergunta. */
  function retry(message: ChatMessage) {
    const question = [...messages].reverse().find((m) => m.role === 'user')?.content;
    if (!question || generating) return;
    patch(message.id, { state: 'gerando', content: '', thinking: false, error: undefined, sources: undefined });
    void ask(question, message.id, true, message.answerKind === 'web');
  }

  function openConversation(id: string | null) {
    setListOpen(false);
    setText('');
    setParams(id ? { conversa: id } : {});
  }

  async function removeConversation() {
    if (!conversationParam) return;
    const ok = await confirmar.remover({
      titulo: 'Excluir conversa?',
      mensagem: `"${current?.title ?? 'Esta conversa'}" e todas as mensagens serão removidas. Os documentos continuam.`,
    });
    if (!ok) return;
    try {
      await api.deleteConversation(conversationParam);
      toast.ok('Conversa excluída');
      openConversation(null);
      await conversations.reload();
    } catch (e) {
      toast.err('Não foi possível excluir', e instanceof Error ? e.message : undefined);
    }
  }

  const options = (documents.data ?? []).map((d) => ({ valor: d.id, rotulo: d.filename }));
  const noDocuments = documents.data && documents.data.length === 0;
  const useWeb = answerFrom === 'web';

  return (
    <div className="app-chat">
      <CabecalhoPagina
        titulo={current?.title ?? 'Chat'}
        icone="message-square"
        acoes={
          <>
            <Botao
              rotulo="Conversas"
              icone="history"
              severidade="secundario"
              disabled={generating}
              onClick={() => {
                setListOpen(true);
                void conversations.reload();
              }}
            />
            {conversationParam && (
              <Botao
                rotulo="Excluir"
                icone="trash-2"
                severidade="secundario"
                disabled={generating}
                onClick={() => void removeConversation()}
              />
            )}
            <Botao
              rotulo="Nova conversa"
              icone="plus"
              severidade="secundario"
              disabled={(!messages.length && !conversationParam) || generating}
              onClick={() => openConversation(null)}
            />
          </>
        }
      />

      <Dialogo
        aberto={listOpen}
        aoFechar={() => setListOpen(false)}
        titulo="Conversas"
        subtitulo="Da mais recente para a mais antiga"
        icone="history"
        aparencia="lateral"
      >
        {conversations.error ? (
          <Alerta severidade="err" titulo="Não foi possível carregar as conversas" mensagem={conversations.error.message} />
        ) : conversations.data?.length ? (
          <Lista rotulo="Conversas salvas">
            {conversations.data.map((c) => (
              <ItemLista
                key={c.id}
                titulo={c.title}
                icone="message-square"
                ativo={c.id === conversationParam}
                onClick={() => openConversation(c.id)}
              >
                {formatDataHoraBr(new Date(c.updated_at))}
              </ItemLista>
            ))}
          </Lista>
        ) : (
          <Vazio
            titulo={conversations.loading ? 'Carregando…' : 'Nenhuma conversa ainda'}
            descricao="As conversas ficam salvas aqui assim que você faz a primeira pergunta."
            icone="history"
          />
        )}
      </Dialogo>

      {loadError && (
        <Alerta
          severidade="err"
          titulo="Não foi possível abrir a conversa"
          mensagem={loadError}
          acoes={<Botao rotulo="Nova conversa" tamanho="pequeno" onClick={() => openConversation(null)} />}
        />
      )}

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
          <div className="app-chat-documentos">
            <CampoSelectMultiplo
              rotulo="Documentos da pergunta"
              dica="As respostas usam só os documentos escolhidos, a não ser que você peça para pesquisar na internet."
              placeholder={documents.loading ? 'Carregando…' : 'Escolha um ou mais documentos'}
              opcoes={options}
              valor={selectedIds}
              aoMudar={setSelectedIds}
              comBusca
              botaoLimpar
            />
            <Botao
              rotulo="Selecionar todos"
              icone="check"
              severidade="secundario"
              disabled={!options.length || selectedIds.length === options.length}
              onClick={() => setSelectedIds(options.map((o) => o.valor))}
            />
          </div>
          <div className="app-chat-conversa">
            <Conversa
              rotulo="Conversa com os documentos"
              larguraMaxima="52rem"
              vazio={
                loadingConversation ? (
                  <Vazio titulo="Abrindo a conversa…" icone="history" />
                ) : (
                  <Vazio
                    titulo="Pergunte sobre seus documentos"
                    descricao="Escolha os documentos acima e escreva uma pergunta. A primeira resposta demora mais: o modelo é carregado na memória."
                    icone="bot"
                  />
                )
              }
              campo={
                <CampoMensagem
                  valor={text}
                  aoMudar={setText}
                  aoEnviar={(question) => {
                    setText('');
                    send(question, useWeb);
                  }}
                  gerando={generating}
                  aoParar={() => abortRef.current?.abort()}
                  desabilitado={(!useWeb && !selectedIds.length) || loadingConversation}
                  placeholder={
                    useWeb
                      ? 'Escreva sua pergunta (será enviada ao buscador)'
                      : selectedIds.length
                        ? 'Escreva sua pergunta'
                        : 'Escolha ao menos um documento'
                  }
                  maxCaracteres={4000}
                  acoesExtras={
                    <div className="app-campo-opcoes">
                      <MenuSuspenso
                        icone="plus"
                        aria-label="Mais opções"
                        dica="Mais opções"
                        semSeta
                        severidade="secundario"
                        aparencia="fantasma"
                        formato="pilula"
                        direcao="cima"
                        alinhamento="inicio"
                        larguraMenu="16rem"
                        desabilitado={generating}
                        itens={[
                          { tipo: 'titulo', rotulo: 'Responder com' },
                          { id: 'documents', rotulo: 'Documentos', icone: 'file-text', ativo: !useWeb },
                          { id: 'web', rotulo: 'Busca na internet', icone: 'globe', ativo: useWeb },
                          { tipo: 'divisor' },
                          { id: 'upload', rotulo: 'Enviar PDF', icone: 'upload' },
                        ]}
                        aoEscolher={(id) => {
                          if (id === 'upload') navigate('/documentos');
                          else setAnswerFrom(id === 'web' ? 'web' : 'documents');
                        }}
                      />
                      {useWeb && (
                        <Chip
                          rotulo="Busca na internet"
                          aoRemover={generating ? undefined : () => setAnswerFrom('documents')}
                        />
                      )}
                    </div>
                  }
                />
              }
            >
              {messages.map((m, index) => {
                if (m.role === 'user') {
                  return (
                    <Mensagem key={m.id} autor="usuario" nome="Você" hora={m.createdAt}>
                      {m.content}
                    </Mensagem>
                  );
                }
                const isWeb = m.answerKind === 'web';
                // Só a última resposta oferece a busca, e nunca durante a geração.
                const canSearchWeb = index === messages.length - 1 && m.state === 'concluida' && !isWeb;
                const offerProminently = canSearchWeb && m.answerKind === 'not_found';
                return (
                  <Mensagem
                    key={m.id}
                    autor="assistente"
                    nome={isWeb ? 'Celke IA · Resposta da internet' : 'Celke IA'}
                    avatar={<span className="app-avatar-ia" aria-hidden="true">IA</span>}
                    estado={m.state}
                    erro={m.error}
                    aoTentarNovamente={index === messages.length - 1 ? () => retry(m) : undefined}
                    copiavel
                    acoes={
                      canSearchWeb && !offerProminently ? (
                        <Botao
                          rotulo="Pesquisar na internet"
                          icone="globe"
                          tamanho="pequeno"
                          severidade="secundario"
                          title={WEB_SEARCH_NOTICE}
                          onClick={() => searchWeb(index)}
                        />
                      ) : undefined
                    }
                    rodape={
                      m.sources?.length || offerProminently ? (
                        <>
                          {m.sources?.length ? <Referencias itens={m.sources.map(toReference)} /> : null}
                          {offerProminently && (
                            <Alerta
                              severidade="info"
                              titulo="Os documentos não têm essa resposta"
                              mensagem={WEB_SEARCH_NOTICE}
                              posicaoAcoes="abaixo"
                              acoes={
                                <Botao
                                  rotulo="Pesquisar na internet"
                                  icone="globe"
                                  tamanho="pequeno"
                                  onClick={() => searchWeb(index)}
                                />
                              }
                            />
                          )}
                        </>
                      ) : undefined
                    }
                  >
                    {m.content ||
                      (m.state === 'gerando' && m.searching ? (
                        <span className="app-pensando">Pesquisando na internet…</span>
                      ) : m.state === 'gerando' && m.thinking ? (
                        <span className="app-pensando">
                          {isWeb ? 'Analisando os resultados da internet…' : 'Analisando os trechos dos documentos…'}
                        </span>
                      ) : undefined)}
                  </Mensagem>
                );
              })}
            </Conversa>
          </div>
        </>
      )}
    </div>
  );
}
