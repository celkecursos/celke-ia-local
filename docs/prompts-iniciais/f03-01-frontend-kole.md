# Frontend React com o Kole

**Etapa:** 3 de 5
**Requer:** etapa 2

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar as telas de Chat, Documentos e Status com o layout `@celke/kole-react`.
> **O que você precisa fazer:** nada. Ao final, a aplicação já abre no navegador.

## Prompt

Crie o frontend do **Celke IA Local** em React, TypeScript e Vite, com o `@celke/kole-react` e nginx com proxy da API.

Regras desta etapa:

- Crie os arquivos com **exatamente** o conteúdo indicado, sem melhorar nem reformatar. O conteúdo já foi
  testado junto; uma alteração aqui quebra outra etapa.
- Não pergunte nada ao usuário: as decisões estão neste prompt e em `docs/configuracao.md`.
- Mostre ao usuário as seções **Orientação** (antes de começar e ao terminar), com as suas palavras só onde
  houver marcador a trocar. Se o terminal não permitir mostrar agora, inclua no seu relatório final.
- Rode tudo o que está em **Verificação** e corrija o que falhar antes de terminar.
- Nunca mostre o valor de `POSTGRES_PASSWORD` nem de `SEARXNG_SECRET`.

`frontend/.dockerignore`:

``````text
node_modules
dist
.env
*.log
``````

`frontend/Dockerfile`:

``````dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_MAX_UPLOAD_MB=25
ENV VITE_MAX_UPLOAD_MB=$VITE_MAX_UPLOAD_MB

# Testes e verificação de tipos (docker compose --profile test run --rm frontend-tests)
FROM build AS test
CMD ["sh", "-c", "npm run typecheck && npm test"]

FROM build AS bundle
RUN npm run build

FROM nginx:1.30-alpine AS runtime
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=bundle /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
``````

`frontend/index.html`:

``````html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/logo.svg" />
    <title>Celke IA Local</title>
    <!-- tema e densidade antes da primeira pintura: scriptTemaInicial() da @celke/kole-react -->
    <script>(function(){var p={};try{p=JSON.parse(localStorage.getItem("lp-preferencias")||"{}")||{}}catch(e){}var t=p.tema||"sistema";var h=document.documentElement;h.setAttribute("data-theme",{"claro":"light","escuro":"dark","sistema":"system"}[t]||"light");var d={"compacta":"density-compact","confortavel":"density-comfortable","espacosa":"density-cozy"}[p.densidade||"confortavel"];if(d)h.classList.add(d)})();</script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
``````

`frontend/nginx.conf.template`:

``````nginx
# Serve o React e repassa /api ao backend pela rede interna do Docker.
# O navegador só fala com este servidor (mesma origem, sem CORS).
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;

    client_max_body_size ${MAX_UPLOAD_MB}m;

    # add_header de um location substitui os do server: os de segurança se repetem em cada um.
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Streaming do chat: entrega cada pedaço da resposta assim que chega.
        proxy_buffering off;
        proxy_cache off;
        # O modelo pode levar minutos para carregar na primeira pergunta.
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header Referrer-Policy same-origin always;
        try_files $uri =404;
    }

    location / {
        add_header Cache-Control "no-cache";
        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header Referrer-Policy same-origin always;
        try_files $uri /index.html;
    }
}
``````

`frontend/package.json`:

``````json
{
  "name": "celke-ia-local-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "preview": "vite preview"
  },
  "dependencies": {
    "@celke/kole-react": "^0.2.0",
    "lucide-react": "^1.60.0",
    "react": "^19.3.1",
    "react-dom": "^19.3.1",
    "react-router": "^8.5.1"
  },
  "devDependencies": {
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "@vitejs/plugin-react": "^6.1.2",
    "typescript": "~6.0.3",
    "vite": "^8.3.5",
    "vitest": "^5.0.5"
  }
}
``````

`frontend/public/logo.svg`:

``````xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#ff9a2e"/><path d="M18 22a6 6 0 0 1 6-6h16a6 6 0 0 1 6 6v14a6 6 0 0 1-6 6H30l-8 7v-7h-0a4 4 0 0 1-4-4z" fill="#0b1a36"/><circle cx="27" cy="29" r="3" fill="#ff9a2e"/><circle cx="37" cy="29" r="3" fill="#ff9a2e"/></svg>
``````

`frontend/src/components/StatusLabel.tsx`:

``````tsx
import { Status } from '@celke/kole-react';
import type { DocumentItem } from '../types/api';

type Severidade = 'ok' | 'info' | 'warn' | 'err' | 'neutral';

const LABELS: Record<DocumentItem['status'], { rotulo: string; severidade: Severidade }> = {
  pendente: { rotulo: 'Na fila', severidade: 'neutral' },
  processando: { rotulo: 'Processando', severidade: 'info' },
  pronto: { rotulo: 'Pronto', severidade: 'ok' },
  erro: { rotulo: 'Erro', severidade: 'err' },
};

/** Situação do documento como selo do Kole. */
export function DocumentStatusLabel({ document }: { document: DocumentItem }) {
  if (document.needs_reindex) return <Status rotulo="Reprocessar" severidade="warn" />;
  const { rotulo, severidade } = LABELS[document.status];
  return <Status rotulo={rotulo} severidade={severidade} />;
}

export function OnlineStatus({ online, rotulo }: { online: boolean; rotulo?: string }) {
  return <Status rotulo={rotulo ?? (online ? 'Conectado' : 'Desconectado')} severidade={online ? 'ok' : 'err'} />;
}
``````

`frontend/src/hooks/usePolling.ts`:

``````ts
import { useCallback, useEffect, useRef, useState } from 'react';

interface PollingState<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => Promise<void>;
}

/**
 * Carrega `load` e repete a cada `intervalMs` enquanto `active` for verdadeiro
 * (ex.: enquanto houver documento processando). `intervalMs = 0` não repete.
 */
export function usePolling<T>(load: () => Promise<T>, intervalMs: number, active = true): PollingState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;

  const reload = useCallback(async () => {
    try {
      setData(await loadRef.current());
      setError(undefined);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!active || intervalMs <= 0) return;
    const timer = window.setInterval(() => void reload(), intervalMs);
    return () => window.clearInterval(timer);
  }, [active, intervalMs, reload]);

  return { data, error, loading, reload };
}
``````

`frontend/src/layouts/AppLayout.tsx`:

``````tsx
import { Estrutura } from '@celke/kole-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';

const NAV = [
  {
    itens: [
      { rotulo: 'Chat', icone: 'message-square', rota: '/' },
      { rotulo: 'Documentos', icone: 'file-text', rota: '/documentos' },
      { rotulo: 'Status', icone: 'activity', rota: '/status' },
    ],
  },
];

export function AppLayout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <Estrutura
      marca={{ nome: 'Celke IA Local', subtitulo: 'Chat com seus PDFs', logo: '/logo.svg', href: '/' }}
      nav={NAV}
      rotaAtual={pathname}
      aoNavegar={(rota) => navigate(rota)}
      renderLink={(p) => (
        <Link to={p.href} className={p.className} onClick={p.onClick} aria-current={p['aria-current']}>
          {p.children}
        </Link>
      )}
      busca={false}
      versao="1.0.0"
      rodape={<span>Celke IA Local · os modelos rodam no seu computador com o Ollama</span>}
    >
      <Outlet />
    </Estrutura>
  );
}
``````

`frontend/src/main.tsx`:

``````tsx
import '@celke/kole-react/estilos.css';
import './styles.css';
import { ProvedorUi, registrarIcones } from '@celke/kole-react';
import { Activity, Bot, Cpu, Database, Globe, Server } from 'lucide-react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { router } from './router';

// Ícones usados pelo nome que não vêm registrados no Kole
registrarIcones({ activity: Activity, bot: Bot, cpu: Cpu, database: Database, globe: Globe, server: Server });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProvedorUi>
      <RouterProvider router={router} />
    </ProvedorUi>
  </StrictMode>,
);
``````

`frontend/src/pages/ChatPage.tsx`:

``````tsx
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
        className="app-chat-cabecalho"
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
``````

`frontend/src/pages/DocumentsPage.tsx`:

``````tsx
import {
  AcaoLinha,
  Alerta,
  Botao,
  CabecalhoPagina,
  CampoAnexo,
  Card,
  formatBytes,
  formatDataHoraBr,
  Progresso,
  Tabela,
  useConfirmacao,
  useToast,
  type Anexo,
  type CampoAnexoRef,
  type Coluna,
} from '@celke/kole-react';
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { DocumentStatusLabel } from '../components/StatusLabel';
import { usePolling } from '../hooks/usePolling';
import { api, uploadDocument } from '../services/api';
import type { DocumentItem } from '../types/api';

// Mesmo limite do backend (MAX_UPLOAD_MB) e do nginx (client_max_body_size).
const MAX_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB ?? 25);

interface UploadState {
  name: string;
  percent: number;
}

export function DocumentsPage() {
  const toast = useToast();
  const confirmar = useConfirmacao();
  const navigate = useNavigate();
  const anexoRef = useRef<CampoAnexoRef>(null);
  const [selected, setSelected] = useState<Anexo[]>([]);
  const [upload, setUpload] = useState<UploadState | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [processing, setProcessing] = useState(false);
  const docs = usePolling(
    async () => {
      const items = await api.documents();
      setProcessing(items.some((d) => d.status === 'pendente' || d.status === 'processando'));
      return items;
    },
    2000,
    processing,
  );

  async function sendFiles() {
    const files = selected.map((a) => anexoRef.current?.arquivoDe(a)).filter((f): f is File => !!f);
    for (const file of files) {
      setUpload({ name: file.name, percent: 0 });
      try {
        await uploadDocument(file, (percent) => setUpload({ name: file.name, percent }));
        toast.ok('PDF enviado', `${file.name} está sendo processado.`);
      } catch (e) {
        toast.err(`Não foi possível enviar ${file.name}`, e instanceof Error ? e.message : undefined);
      }
    }
    setUpload(null);
    setSelected([]);
    await docs.reload();
    setProcessing(true);
  }

  async function remove(doc: DocumentItem) {
    const ok = await confirmar.remover({
      titulo: 'Excluir documento?',
      mensagem: `"${doc.filename}" e todos os trechos indexados serão removidos. Esta ação não pode ser desfeita.`,
    });
    if (!ok) return;
    setBusyId(doc.id);
    try {
      await api.deleteDocument(doc.id);
      toast.ok('Documento excluído');
      await docs.reload();
    } catch (e) {
      toast.err('Não foi possível excluir', e instanceof Error ? e.message : undefined);
    } finally {
      setBusyId(null);
    }
  }

  async function reprocess(doc: DocumentItem) {
    setBusyId(doc.id);
    try {
      await api.reprocess(doc.id);
      toast.info('Reprocessando', doc.filename);
      setProcessing(true);
      await docs.reload();
    } catch (e) {
      toast.err('Não foi possível reprocessar', e instanceof Error ? e.message : undefined);
    } finally {
      setBusyId(null);
    }
  }

  const columns: Coluna<DocumentItem>[] = [
    {
      campo: 'filename',
      rotulo: 'Arquivo',
      destaque: true,
      render: (d) => (
        <div className="app-doc-nome">
          <span>{d.filename}</span>
          {d.status === 'erro' && d.error_message && <small className="app-doc-erro">{d.error_message}</small>}
          {d.needs_reindex && <small className="app-doc-erro">Indexado com outro modelo de embeddings.</small>}
        </div>
      ),
    },
    { campo: 'size_bytes', rotulo: 'Tamanho', alinhamento: 'direita', formato: (v) => formatBytes(Number(v)) },
    { campo: 'page_count', rotulo: 'Páginas', alinhamento: 'direita', formato: (v) => (v == null ? '–' : String(v)) },
    { campo: 'created_at', rotulo: 'Enviado em', formato: (v) => formatDataHoraBr(new Date(String(v))) },
    { campo: 'status', rotulo: 'Situação', render: (d) => <DocumentStatusLabel document={d} /> },
  ];

  return (
    <div className="app-pagina">
      <CabecalhoPagina titulo="Documentos" icone="file-text" trilha>
        Envie PDFs com texto selecionável. Cada arquivo é dividido em trechos e indexado para o chat.
      </CabecalhoPagina>

      <Card titulo="Enviar PDFs">
        <CampoAnexo
          ref={anexoRef}
          rotulo="Arquivos PDF"
          dica={`Até ${MAX_MB} MB por arquivo. PDFs digitalizados como imagem não são lidos (sem OCR).`}
          accept="application/pdf,.pdf"
          maxTamanho={MAX_MB * 1024 * 1024}
          valor={selected}
          aoMudar={setSelected}
          disabled={!!upload}
        />
        {upload && (
          <div className="app-upload">
            <span>Enviando {upload.name}</span>
            <Progresso valor={upload.percent} mostrarValor="fim" rotulo={`Envio de ${upload.name}`} />
          </div>
        )}
        <div className="app-acoes">
          <Botao
            rotulo={selected.length > 1 ? `Enviar ${selected.length} arquivos` : 'Enviar'}
            icone="cloud-upload"
            disabled={!selected.length}
            carregando={!!upload}
            onClick={sendFiles}
          />
        </div>
      </Card>

      {docs.error && !docs.data && (
        <Alerta severidade="err" titulo="Não foi possível carregar os documentos" mensagem={docs.error.message} />
      )}

      <Card titulo="Documentos cadastrados" corpoSemEspaco>
        <Tabela
          colunas={columns}
          registros={docs.data ?? []}
          carregando={docs.loading}
          erro={docs.error && !!docs.data ? docs.error.message : undefined}
          aoRecarregar={docs.reload}
          vazioTitulo="Nenhum documento ainda"
          vazioDescricao="Envie um PDF acima para começar."
          vazioIcone="file-text"
          acoes={(d) => (
            <>
              {d.status === 'pronto' && !d.needs_reindex && (
                <AcaoLinha icone="message-square" rotulo="Conversar" severidade="pri" onClick={() => navigate(`/?doc=${d.id}`)} />
              )}
              {(d.status === 'erro' || d.needs_reindex) && (
                <AcaoLinha icone="refresh-cw" rotulo="Reprocessar" carregando={busyId === d.id} onClick={() => reprocess(d)} />
              )}
              <AcaoLinha
                icone="trash-2"
                rotulo="Excluir"
                severidade="err"
                disabled={d.status === 'processando'}
                carregando={busyId === d.id}
                onClick={() => remove(d)}
              />
            </>
          )}
        />
      </Card>
    </div>
  );
}
``````

`frontend/src/pages/NotFoundPage.tsx`:

``````tsx
import { Botao, Vazio } from '@celke/kole-react';
import { useNavigate } from 'react-router';

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <Vazio titulo="Página não encontrada" descricao="O endereço não existe nesta aplicação." icone="circle-question-mark">
      <Botao rotulo="Ir para o chat" icone="message-square" onClick={() => navigate('/')} />
    </Vazio>
  );
}
``````

`frontend/src/pages/StatusPage.tsx`:

``````tsx
import { Alerta, Botao, CabecalhoPagina, Card, Indicador, Indicadores } from '@celke/kole-react';
import { useNavigate } from 'react-router';
import { OnlineStatus } from '../components/StatusLabel';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

export function StatusPage() {
  const navigate = useNavigate();
  const stats = usePolling(api.stats, 5000);
  const status = usePolling(api.status, 10000);
  const s = status.data;
  const modelsMissing = s?.ollama.online && !(s.ollama.chat_model.installed && s.ollama.embedding_model.installed);

  return (
    <div className="app-pagina">
      <CabecalhoPagina
        titulo="Status"
        icone="activity"
        acoes={
          <>
            <Botao rotulo="Enviar PDF" icone="upload" onClick={() => navigate('/documentos')} />
            <Botao rotulo="Iniciar conversa" icone="message-square" severidade="secundario" onClick={() => navigate('/')} />
          </>
        }
      >
        Situação dos documentos e dos serviços. As respostas são geradas por um modelo de IA rodando no seu computador.
      </CabecalhoPagina>

      {stats.error && <Alerta severidade="err" titulo="Não foi possível carregar os números" mensagem={stats.error.message} />}
      {s && !s.ollama.online && (
        <Alerta
          severidade="err"
          titulo="Ollama desconectado"
          mensagem={s.ollama.error ?? 'Verifique o container do Ollama: docker compose logs ollama'}
        />
      )}
      {modelsMissing && (
        <Alerta
          severidade="warn"
          titulo="Modelos ainda não instalados"
          mensagem="O download inicial dos modelos pode levar alguns minutos. Acompanhe com: docker compose logs -f ollama-init"
        />
      )}

      <Indicadores>
        <Indicador rotulo="Documentos cadastrados" valor={stats.data?.total ?? '–'} icone="file-text" carregando={stats.loading} />
        <Indicador
          rotulo="Prontos para o chat"
          valor={stats.data?.ready ?? '–'}
          icone="circle-check"
          cor="var(--ok-solid)"
          carregando={stats.loading}
        />
        <Indicador
          rotulo="Processando"
          valor={stats.data?.processing ?? '–'}
          icone="loader-circle"
          cor="var(--info-solid)"
          carregando={stats.loading}
        />
        <Indicador
          rotulo="Com erro"
          valor={stats.data?.error ?? '–'}
          icone="triangle-alert"
          cor="var(--err-solid)"
          carregando={stats.loading}
        />
      </Indicadores>

      <Card titulo="Serviços" subtitulo="Atualizado a cada 10 segundos">
        {status.error ? (
          <Alerta severidade="err" titulo="Backend indisponível" mensagem={status.error.message} />
        ) : (
          <ul className="app-lista-servicos">
            <li>
              <span>Backend (API)</span>
              <OnlineStatus online={!!s?.backend.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>Ollama</span>
              <OnlineStatus online={!!s?.ollama.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>
                Modelo de chat <code>{s?.ollama.chat_model.name}</code>
              </span>
              <OnlineStatus online={!!s?.ollama.chat_model.installed} rotulo={s?.ollama.chat_model.installed ? 'Instalado' : 'Ausente'} />
            </li>
            <li>
              <span>
                Modelo de embeddings <code>{s?.ollama.embedding_model.name}</code>
              </span>
              <OnlineStatus
                online={!!s?.ollama.embedding_model.installed}
                rotulo={s?.ollama.embedding_model.installed ? 'Instalado' : 'Ausente'}
              />
            </li>
            <li>
              <span>ChromaDB (banco vetorial)</span>
              <OnlineStatus online={!!s?.vector_store.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>PostgreSQL (documentos e conversas)</span>
              <OnlineStatus online={!!s?.database.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>SearXNG (busca na internet, só quando você pede)</span>
              <OnlineStatus online={!!s?.web_search.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
          </ul>
        )}
      </Card>
    </div>
  );
}
``````

`frontend/src/router.tsx`:

``````tsx
import { createBrowserRouter, Navigate, useLocation } from 'react-router';
import { AppLayout } from './layouts/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { StatusPage } from './pages/StatusPage';

// Endereço antigo do chat: mantém ?conversa= e ?doc= dos links já salvos.
function LegacyChatRedirect() {
  const { search } = useLocation();
  return <Navigate to={`/${search}`} replace />;
}

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <ChatPage /> },
      { path: '/documentos', element: <DocumentsPage /> },
      { path: '/status', element: <StatusPage /> },
      { path: '/chat', element: <LegacyChatRedirect /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
``````

`frontend/src/services/api.ts`:

``````ts
import type {
  ChatDocument,
  ChatEvent,
  ChatRequest,
  Conversation,
  ConversationDetail,
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
  conversations: () => request<{ items: Conversation[] }>('/conversations').then((r) => r.items),
  conversation: (id: string) => request<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id: string) =>
    request<void>(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
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
``````

`frontend/src/services/sse.test.ts`:

``````ts
import { describe, expect, it } from 'vitest';
import { parseSseBlock, readSse } from './sse';

function streamOf(...parts: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const p of parts) controller.enqueue(encoder.encode(p));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const e of readSse(stream)) events.push(e);
  return events;
}

describe('parseSseBlock', () => {
  it('lê os oito tipos de evento', () => {
    expect(parseSseBlock('event: searching\ndata: {}')).toEqual({ type: 'searching' });
    expect(parseSseBlock('event: not_found\ndata: {}')).toEqual({ type: 'not_found' });
    expect(parseSseBlock('event: conversation\ndata: {"id": "c1", "title": "Pergunta"}')).toEqual({
      type: 'conversation',
      id: 'c1',
      title: 'Pergunta',
    });
    expect(parseSseBlock('event: token\ndata: {"text": "Olá"}')).toEqual({ type: 'token', text: 'Olá' });
    expect(parseSseBlock('event: done\ndata: {}')).toEqual({ type: 'done' });
    expect(parseSseBlock('event: thinking\ndata: {}')).toEqual({ type: 'thinking' });
    expect(parseSseBlock('event: error\ndata: {"codigo": "x", "mensagem": "falhou"}')).toEqual({
      type: 'error',
      code: 'x',
      message: 'falhou',
    });
    expect(parseSseBlock('event: sources\ndata: []')).toEqual({ type: 'sources', sources: [] });
  });

  it('ignora eventos desconhecidos e blocos sem dados', () => {
    expect(parseSseBlock('event: ping\ndata: {}')).toBeNull();
    expect(parseSseBlock(': comentário')).toBeNull();
  });
});

describe('readSse', () => {
  it('junta blocos partidos entre pedaços do stream', async () => {
    const events = await collect(
      streamOf('event: token\ndata: {"te', 'xt": "Ol"}\n\nevent: token\n', 'data: {"text": "á"}\n\nevent: done\ndata: {}\n\n'),
    );

    expect(events).toEqual([{ type: 'token', text: 'Ol' }, { type: 'token', text: 'á' }, { type: 'done' }]);
  });

  it('aceita quebras de linha \\r\\n e o último bloco sem linha em branco', async () => {
    const events = await collect(streamOf('event: token\r\ndata: {"text": "a"}\r\n\r\nevent: done\r\ndata: {}'));

    expect(events).toEqual([{ type: 'token', text: 'a' }, { type: 'done' }]);
  });
});
``````

`frontend/src/services/sse.ts`:

``````ts
import type { ChatEvent, Source } from '../types/api';

/** Converte um bloco `event: x\ndata: {...}` num evento do chat (ou `null` se não reconhecido). */
export function parseSseBlock(block: string): ChatEvent | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  const payload = JSON.parse(data.join('\n'));
  switch (event) {
    case 'conversation':
      return { type: 'conversation', id: String(payload.id), title: String(payload.title ?? '') };
    case 'searching':
      return { type: 'searching' };
    case 'not_found':
      return { type: 'not_found' };
    case 'sources':
      return { type: 'sources', sources: payload as Source[] };
    case 'thinking':
      return { type: 'thinking' };
    case 'token':
      return { type: 'token', text: String(payload.text ?? '') };
    case 'done':
      return { type: 'done' };
    case 'error':
      return { type: 'error', code: String(payload.codigo ?? 'erro'), message: String(payload.mensagem ?? 'Erro') };
    default:
      return null;
  }
}

/**
 * Lê um stream SSE em pedaços. Os blocos podem chegar partidos entre dois
 * pedaços; o que sobra fica guardado até o próximo.
 */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
      let end = buffer.indexOf('\n\n');
      while (end !== -1) {
        const parsed = parseSseBlock(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (parsed) yield parsed;
        end = buffer.indexOf('\n\n');
      }
      if (done) break;
    }
    if (buffer.trim()) {
      const parsed = parseSseBlock(buffer);
      if (parsed) yield parsed;
    }
  } finally {
    reader.releaseLock();
  }
}
``````

`frontend/src/styles.css`:

``````css
/* Ajustes do app sobre o Kole: só tokens do tema (tokens.css), sem cores fixas. */

.app-acoes {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.75rem;
}

.app-upload {
  display: grid;
  gap: 0.375rem;
  margin-top: 0.75rem;
  font-size: var(--fs-caption);
  color: var(--t3);
}

.app-doc-nome {
  display: grid;
  gap: 0.125rem;
  min-width: 0;
  overflow-wrap: anywhere;
}

.app-doc-erro {
  color: var(--err-fg);
  font-weight: 400;
}

/* Espaço igual entre os blocos da página (cabeçalho, alertas, indicadores, cards). */
.app-pagina {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.app-lista-servicos {
  list-style: none;
  margin: 0;
  padding: 0;
}

.app-lista-servicos li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.625rem 0;
  border-bottom: var(--hairline) solid var(--border);
  color: var(--t2);
}

.app-lista-servicos li:last-child {
  border-bottom: 0;
}

.app-lista-servicos code {
  color: var(--t3);
  overflow-wrap: anywhere;
}

/*
 * O chat ocupa exatamente a área de conteúdo da Estrutura: cabeçalho e
 * documentos ficam sempre visíveis e só a Conversa rola.
 */
.lp-content:has(> .lp-content-inner > .app-chat) {
  display: flex;
  flex-direction: column;
}

.lp-content-inner:has(> .app-chat) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.app-chat {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.app-chat > * {
  flex: none;
}

.app-chat > .app-chat-conversa {
  flex: 1;
  display: flex;
  flex-direction: column;
  /* janela muito baixa: a página volta a rolar em vez de esmagar a conversa */
  min-height: 16rem;
  border: var(--hairline) solid var(--border);
  border-radius: var(--r-card);
  background: var(--surface);
  overflow: hidden;
}

.app-chat-conversa > * {
  flex: 1;
  min-height: 0;
}

/* Título da conversa em até 2 linhas; sem espaço ao lado dele, os botões descem para a linha de baixo. */
.app-chat-cabecalho .lp-cab-topo {
  flex-wrap: wrap;
}

.app-chat-cabecalho .lp-cab-titulos {
  flex: 1 1 14rem;
}

.app-chat-cabecalho .lp-cab-titulo {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
}

@media (max-width: 40rem) {
  .app-chat-cabecalho.lp-cab {
    padding: 1rem;
  }

  .app-chat-cabecalho .lp-cab-topo {
    gap: 0.75rem;
  }

  .app-chat-cabecalho .lp-cab-tile {
    width: 2.25rem;
    height: 2.25rem;
  }

  .app-chat-cabecalho .lp-cab-titulos {
    flex-basis: 0;
  }

  .app-chat-cabecalho .lp-cab-titulo {
    font-size: var(--fs-corpo);
    font-weight: 700;
  }

  .app-chat-cabecalho .lp-cab-acoes {
    flex-basis: 100%;
  }
}

/* Botão "Selecionar todos" alinhado à caixa do campo, ao lado do rótulo e abaixo dele a dica. */
.app-chat-documentos {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.75rem;
}

.app-chat-documentos > :first-child {
  flex: 1 1 16rem;
  min-width: 0;
}

.app-chat-documentos > button {
  margin-top: 1.25rem;
}

.app-campo-opcoes {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  min-width: 0;
}

.app-avatar-ia {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--pri-bg);
  color: var(--pri);
  font-size: var(--fs-caption);
  font-weight: 800;
}

.app-pensando {
  color: var(--t3);
  font-style: italic;
}
``````

`frontend/src/types/api.ts`:

``````ts
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
``````

`frontend/tsconfig.json`:

``````json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
``````

`frontend/vite.config.ts`:

``````ts
/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Em desenvolvimento (npm run dev), o Vite repassa /api para o backend.
// No Docker, quem faz isso é o nginx (nginx.conf).
export default defineConfig({
  plugins: [react()],
  resolve: { dedupe: ['react', 'react-dom'] },
  server: {
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: { environment: 'node' },
});
``````

Por último, gere o `frontend/package-lock.json` sem exigir Node no computador. Rode na raiz do projeto, trocando
`<pasta frontend absoluta>` pelo caminho real (no Git Bash do Windows, prefixe o comando com `MSYS_NO_PATHCONV=1`):

```bash
docker run --rm -v "<pasta frontend absoluta>:/app" -w /app node:24-alpine npm install --package-lock-only --no-audit --no-fund
```

## Verificação

```bash
docker compose --profile test run --rm --build frontend-tests
docker compose up -d --build
docker compose ps                                 # todos healthy; só o frontend com porta
curl -s http://localhost:<porta>/api/status       # todos os serviços online
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<porta>/documentos   # 200
```

Use a porta de `docs/configuracao.md`. No Windows PowerShell, escreva `curl.exe`.

## Depois de executar

```bash
git add frontend
git commit -m "feat: cria o frontend com chat, documentos e status"
```

## Orientação ao terminar

> **Pronto:** a aplicação já abre em http://localhost:<porta>, mas ainda vou testar tudo. Continue sem fazer nada.
