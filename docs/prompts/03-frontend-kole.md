# Etapa 3 — Frontend React com o Kole

## Contexto

O backend responde em `/api` (etapa 2). Nesta etapa você cria o frontend em `frontend/`: React 19 com
TypeScript e Vite, React Router e o layout da Celke, o pacote **`@celke/kole-react`** do npm. O nginx
serve o build e repassa `/api` ao backend, então o navegador só fala com uma origem.

## Antes de escrever código

1. Instale e leia a biblioteca: `npm view @celke/kole-react` e, depois do `npm install`, o
   `node_modules/@celke/kole-react/README.md` e os tipos em `node_modules/@celke/kole-react/dist`
   (`index.d.ts` e `components/*/*.d.ts`). Use só componentes, props e exports que existem. As props
   são em português (`rotulo`, `valor`, `aoMudar`…) e ficam como estão, mesmo com a regra de nomes em
   inglês no código do projeto.
2. Componentes do Kole a usar: `ProvedorUi` (tema claro/escuro, toasts e confirmação), `Estrutura`
   (menu lateral), `CabecalhoPagina`, `Card`, `Indicador`/`Indicadores`, `Status`, `Alerta`, `Botao`,
   `AcaoLinha`, `Tabela`, `CampoAnexo`, `Progresso`, `CampoSelectMultiplo`, `Vazio`, `Dialogo`,
   `Lista`/`ItemLista`, `useToast`,
   `useConfirmacao` (com `.remover()`), `registrarIcones`, `formatBytes`, `formatDataHoraBr` e os
   componentes de conversa `Conversa`, `Mensagem`, `CampoMensagem` e `Referencias`.

## Dependências (`frontend/package.json`)

```json
"dependencies": {
  "@celke/kole-react": "^0.1.0",
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
```

Scripts: `dev` (`vite`), `build` (`tsc --noEmit && vite build`), `typecheck` (`tsc --noEmit`), `test`
(`vitest run`). Gere o `package-lock.json` com `npm install`; se a máquina não tiver Node, rode
`docker run --rm -v "$PWD/frontend":/app -w /app node:24-alpine npm install`.

`tsconfig.json`: `ES2022`, `moduleResolution: bundler`, `jsx: react-jsx`, `strict`,
`noUnusedLocals`, `noUnusedParameters`, `noEmit`, `types: ["vite/client"]`, `include: ["src"]`.
`vite.config.ts` (com `/// <reference types="vitest/config" />`): plugin React,
`resolve.dedupe: ['react', 'react-dom']`, proxy de `/api` para `process.env.VITE_API_PROXY ??
'http://localhost:8000'` em desenvolvimento e `test.environment: 'node'`. `index.html` em `pt-BR`
com título "Celke IA Local" e um `public/logo.svg` simples (balão de conversa).

## Organização

```
src/main.tsx               importa '@celke/kole-react/estilos.css' e './styles.css'; registra os
                           ícones activity, bot, cpu, database, globe e server do lucide-react com registrarIcones;
                           <ProvedorUi><RouterProvider router={router} /></ProvedorUi>
src/router.tsx             createBrowserRouter: layout com '/' (chat), '/documentos', '/status', '/chat' (redireciona para '/', mantendo a query string) e '*'
src/layouts/AppLayout.tsx  Estrutura com marca "Celke IA Local" / "Chat com seus PDFs", menu Chat
                           (message-square), Documentos (file-text) e Status (activity), rotaAtual,
                           aoNavegar, renderLink com o Link do React Router, busca={false}, rodapé
src/types/api.ts           tipos das respostas da API e ChatEvent
src/services/sse.ts        parseSseBlock e readSse (gerador assíncrono)
src/services/api.ts        request() com ApiError, api.*, uploadDocument (XMLHttpRequest), streamChat
src/hooks/usePolling.ts    carrega e repete enquanto `active`
src/components/StatusLabel.tsx  DocumentStatusLabel e OnlineStatus (Status do Kole)
src/pages/ChatPage.tsx, DocumentsPage.tsx, StatusPage.tsx, NotFoundPage.tsx
src/styles.css             ajustes de layout só com as variáveis do tema (nada de cor fixa)
```

O conteúdo de Status e de Documentos fica num `<div className="app-pagina">` (`display: flex`,
`flex-direction: column`, `gap: 1rem`): os componentes do Kole não têm margem externa, e assim o espaço
entre cabeçalho, alertas, indicadores e cards é sempre o mesmo. O contêiner do Chat usa o mesmo `gap`.

## Serviços

- `ApiError(message, status, code)`; a mensagem vem de `erro.mensagem` do backend; 502/504 →
  "O backend não respondeu. Verifique se os containers estão rodando."; falha de rede → "Não foi
  possível conectar ao backend.".
- `uploadDocument(file, onProgress)` com **XMLHttpRequest** (o `fetch` não informa o progresso do
  envio); 413 sem corpo do backend (veio do nginx) → "O arquivo passa do limite de tamanho do
  servidor.".
- `streamChat(body, signal)`: `fetch` POST com `Accept: text/event-stream` e o `AbortSignal`; erro HTTP
  vira `ApiError`; o corpo é lido por `readSse`, que junta blocos partidos entre pedaços, aceita
  `\r\n` e entrega `conversation` (`id`, `title`), `searching`, `sources`, `thinking`, `token`, `not_found`, `done` e `error`
  (com `codigo`/`mensagem` → `code`/`message`). Abortado pelo usuário encerra sem erro.
- `api.conversations()`, `api.conversation(id)` e `api.deleteConversation(id)`.

## Telas

**Status:** `CabecalhoPagina` com botões "Enviar PDF" e "Iniciar conversa"; `Indicadores` com
documentos cadastrados, prontos, processando e com erro (de `/api/documents/stats`, atualizando a cada
5 s); `Alerta` de erro quando o Ollama estiver desconectado e de aviso quando um modelo ainda não
estiver instalado (com o comando `docker compose logs -f ollama-init`); `Card` "Serviços" com backend,
Ollama, modelo de chat, modelo de embeddings, ChromaDB e PostgreSQL, cada um com `Status`, atualizando
a cada 10 s.

**Documentos:** `Card` com `CampoAnexo` (`accept="application/pdf,.pdf"`, `maxTamanho` de
`VITE_MAX_UPLOAD_MB`, padrão 25), guardando o `ref` para obter o `File` com `arquivoDe`; botão Enviar,
que envia os arquivos um por um com `Progresso` e um toast por resultado. `Tabela` com Arquivo (nome
e, abaixo, a mensagem de erro ou o aviso de reindexação), Tamanho (`formatBytes`), Páginas, Enviado em
(`formatDataHoraBr`) e Situação (`Status`: Na fila, Processando, Pronto, Erro ou Reprocessar); estado
vazio; ações por linha com `AcaoLinha`: Conversar (pronto → `/?doc=<id>`), Reprocessar (erro ou
`needs_reindex`) e Excluir (desabilitado enquanto processa, confirmação com
`useConfirmacao().remover()` dizendo que os trechos indexados também serão removidos). A lista é
recarregada a cada 2 s **só enquanto** houver documento na fila ou processando.

**Chat:** a conversa aberta fica na URL (`/?conversa=<id>`): ao recarregar ou escolher na lista, a
página busca `/api/conversations/<id>` e mostra as mensagens gravadas (com as fontes e os erros) e
seleciona os documentos da conversa; conversa inexistente → `Alerta` com botão "Nova conversa".
`CampoSelectMultiplo` com os documentos de `/api/chat/documents` (com busca e botão limpar),
pré-selecionando os `?doc=` da URL e descartando os que não estão prontos. `CabecalhoPagina` com o
título da conversa aberta (ou "Chat") e os botões "Conversas" (ícone `history`, abre um `Dialogo`
`aparencia="lateral"` com uma `Lista` de `ItemLista`, título e data da última mensagem, a aberta
marcada como `ativo`, e `Vazio` quando não houver nenhuma), "Excluir" (só com conversa aberta;
`useConfirmacao().remover()` dizendo que os documentos continuam) e "Nova conversa" (limpa a URL e as
mensagens), todos desabilitados enquanto a resposta é gerada. `Vazio` com link para Documentos quando
não houver documento pronto. Abaixo, `Conversa` (com
`larguraMaxima="52rem"` e estado vazio próprio) num contêiner que preenche o resto da área de
conteúdo da `Estrutura` (o `.lp-content` vira coluna flex só nesta página, via `:has()`): cabeçalho e
seleção de documentos ficam sempre visíveis, só as mensagens rolam e o campo fica fixo embaixo. No
`campo` um `CampoMensagem` (desabilitado sem documento escolhido, `maxCaracteres={4000}`, `gerando` e
`aoParar` que aborta o `AbortController`). Cada pergunta acrescenta a mensagem do usuário
(`Mensagem autor="usuario"`, nome "Você", hora) e a do assistente (`autor="assistente"`, nome
"Celke IA", avatar com "IA", `estado` gerando/concluída/erro, `copiavel`). O pedido leva
`conversation_id` da conversa aberta; sem ela, o evento `conversation` traz o id da conversa criada,
que vai para a URL com `replace` (recarregar continua nela). `aoTentarNovamente` só na **última**
mensagem: manda `retry: true` com a última pergunta, e o backend refaz a resposta sem repetir a
pergunta. Enquanto só chegou `searching`, mostre "Pesquisando na internet…". Enquanto só chegou `thinking`, mostre "Analisando os trechos dos documentos…" (na web, "Analisando os resultados da internet…"); os `token`
são concatenados no conteúdo. As fontes vão no `rodape` como `Referencias` (título `[n] arquivo`,
detalhe "Página N", trecho). Parar mantém o que já chegou (ou "Resposta interrompida.") — o backend
grava o mesmo. O histórico não é enviado: o backend o lê da conversa. Depois de cada resposta, a lista
de conversas é recarregada.

**Busca na internet:** na última resposta, concluída e que não veio da web: com `not_found` (ou
`answer_kind: "not_found"` ao reabrir a conversa), `Alerta` `info` no `rodape` com o título "Os documentos
não têm essa resposta", o texto "Só a pergunta é enviada ao buscador. Os seus PDFs continuam no computador."
e o botão "Pesquisar na internet" (ícone `globe`); nas outras, o mesmo botão pequeno e secundário em `acoes`.
O clique repete a pergunta com `web_search: true`. Resposta da web com o nome "Celke IA · Resposta da internet"
e `Referencias` com `href` e o domínio em `detalhe`. "Tentar novamente" mantém `web_search`. Em Status,
linha do SearXNG.

**Não encontrada:** `Vazio` com botão para o chat.

## Docker

`frontend/Dockerfile`: estágio `build` em `node:24-alpine` (`npm ci`, `ARG`/`ENV` `VITE_MAX_UPLOAD_MB`);
estágio `test` (`npm run typecheck && npm test`); estágio `bundle` (`npm run build`); estágio
`runtime` em `nginx:1.30-alpine`, copiando `nginx.conf.template` para
`/etc/nginx/templates/default.conf.template` e o `dist`, com healthcheck por `wget`.

`nginx.conf.template`: `client_max_body_size ${MAX_UPLOAD_MB}m`; `location /api/` com
`proxy_pass http://backend:8000`, HTTP/1.1, `proxy_buffering off` e `proxy_cache off` (o streaming
chega pedaço a pedaço) e `proxy_read_timeout`/`proxy_send_timeout` de 600 s; `/assets/` com cache de
um ano; `/` com `try_files $uri /index.html` e `no-cache`. Os cabeçalhos `X-Content-Type-Options`,
`X-Frame-Options DENY` e `Referrer-Policy same-origin` vão **em cada location que tiver `add_header`**
(um `add_header` no location anula os do server). `frontend/.dockerignore`: `node_modules`, `dist`,
`.env`, `*.log`.

No `compose.yaml`, acrescente o `frontend` (target `runtime`, `args` e `environment` com
`MAX_UPLOAD_MB`, `ports: "${APP_BIND:-127.0.0.1}:${APP_PORT:-8090}:80"`, depende do `backend`
saudável) e o `frontend-tests` (`profiles: [test]`, target `test`).

## Testes

`src/services/sse.test.ts` com Vitest: os oito tipos de evento, evento desconhecido ignorado, blocos
partidos entre pedaços, `\r\n` e último bloco sem linha em branco.

## Verificação

```bash
docker compose --profile test run --rm --build frontend-tests     # tsc sem erros e testes passando
docker compose up -d --build
docker compose ps                                                 # todos healthy; só o frontend com porta
curl -s http://127.0.0.1:8090/api/health                          # {"status":"ok"} pelo nginx
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/documentos   # 200 (rota do React)
```

Abra http://localhost:8090 e confira o menu, a página de status com os serviços verdes, a de documentos
e o chat, nos temas claro e escuro e numa janela estreita (celular). No chat, faça uma pergunta,
confira o `?conversa=` na URL, recarregue a página (a conversa continua) e abra a lista de conversas.
