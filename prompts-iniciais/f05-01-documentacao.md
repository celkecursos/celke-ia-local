# Documentação e entrega

**Etapa:** 5 de 5
**Requer:** etapa 4

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar o README e o guia para agentes de IA e fazer a entrega final.
> **O que você precisa fazer:** nada por enquanto. No final, mostro como testar no navegador.

## Prompt

Crie a documentação do **Celke IA Local**, copie os prompts para o projeto e crie a branch de homologação.

Regras desta etapa:

- Crie os arquivos com **exatamente** o conteúdo indicado, sem melhorar nem reformatar. O conteúdo já foi
  testado junto; uma alteração aqui quebra outra etapa.
- Não pergunte nada ao usuário: as decisões estão neste prompt e em `docs/configuracao.md`.
- Mostre ao usuário as seções **Orientação** (antes de começar e ao terminar), com as suas palavras só onde
  houver marcador a trocar. Se o terminal não permitir mostrar agora, inclua no seu relatório final.
- Rode tudo o que está em **Verificação** e corrija o que falhar antes de terminar.
- Nunca mostre o valor de `POSTGRES_PASSWORD` nem de `SEARXNG_SECRET`.

Troque `<url-do-repositório>` no `README.md` pela URL do `origin`, se houver. Sem `origin`, mantenha o marcador.

`README.md`:

``````markdown
# Celke IA Local

Chatbot que responde perguntas sobre os seus PDFs com um modelo de IA rodando no seu computador. Você
envia os documentos, o sistema divide o texto em trechos e os indexa, e o chat responde com base nesses
trechos, mostrando as fontes (documento, página e texto). Tudo roda no Docker: não é preciso instalar
Python nem Node.js e não há API paga.

## Índice

- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Requisitos](#requisitos)
- [Executar com Docker](#executar-com-docker)
- [Usar a aplicação](#usar-a-aplicação)
- [Configuração e troca de modelos](#configuração-e-troca-de-modelos)
- [Testes](#testes)
- [Comandos úteis](#comandos-úteis)
- [Dados: preservar ou apagar](#dados-preservar-ou-apagar)
- [Atualizar o projeto](#atualizar-o-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Problemas comuns](#problemas-comuns)
- [Hardware e limitações](#hardware-e-limitações)
- [Segurança](#segurança)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Prompts para recriar o projeto](#prompts-para-recriar-o-projeto)

## Funcionalidades

- **Status:** documentos cadastrados, prontos, processando e com erro (números reais da API); estado do
  backend, do Ollama, dos dois modelos, do ChromaDB e do PostgreSQL; atalhos para enviar PDF e conversar.
- **Documentos:** envio de um ou vários PDFs com barra de progresso; validação de extensão, conteúdo
  (`%PDF-`) e tamanho; processamento em segundo plano com a situação na tabela (na fila, processando,
  pronto, erro); nome, tamanho, páginas e data de envio; exclusão com confirmação, que remove o arquivo,
  os metadados e os vetores; reprocessamento; o mesmo PDF não entra duas vezes (SHA-256).
- **Chat:** escolha de um ou mais documentos; resposta em streaming (aparece enquanto é gerada); botão
  parar; fontes de cada resposta (documento, página e trecho); tentar novamente em caso de erro; copiar
  a resposta; conversas salvas no PostgreSQL (a conversa aberta fica no endereço `/?conversa=<id>`,
  então recarregar a página continua nela); lista das conversas anteriores para reabrir; exclusão de
  conversa com confirmação.
- **Busca na internet (opcional):** quando os PDFs não têm a resposta, o chat avisa e oferece o botão
  **Pesquisar na internet**; as demais respostas têm o mesmo botão, discreto. No campo da pergunta, o
  menu **+** escolhe de onde vem a resposta (com **Busca na internet**, não é preciso selecionar
  documento). Nada é pesquisado sem o clique, e só a pergunta sai do computador. A resposta vem marcada como "Resposta da internet", com os
  links das páginas como fontes. Usa o SearXNG, sem chave nem API paga.
- **RAG:** extração com PyMuPDF página a página, divisão com sobreposição, embeddings no Ollama, vetores
  no ChromaDB com documento e página nos metadados, busca só nos documentos escolhidos e resposta baseada
  nos trechos. Sem trechos relevantes, o sistema diz que não encontrou a informação em vez de inventar.
- **Proteções:** o conteúdo dos PDFs é tratado como dado não confiável (instruções dentro do PDF não
  mudam as regras do assistente), arquivos gravados com nome interno, CORS desligado, Ollama, ChromaDB e
  PostgreSQL e SearXNG sem portas publicadas.

## Arquitetura

```
Navegador ──► frontend (nginx :8090) ──/api──► backend (FastAPI :8000) ──► ollama (:11434)
              React + Kole React                 │                            qwen3:4b, nomic-embed-text
                                                 ├──► chroma (:8000)  vetores dos trechos
                                                 ├──► postgres (:5432) documentos, conversas, mensagens
                                                 ├──► searxng (:8080) busca na internet, só com o clique
                                                 └──► /data           arquivos PDF
```

| Serviço | Função | Porta no seu computador |
|---|---|---|
| `frontend` | nginx com o React; repassa `/api` ao backend (mesma origem, streaming sem buffer) | `127.0.0.1:8090` |
| `backend` | API REST, processamento dos PDFs e RAG | nenhuma |
| `ollama` | Modelo de chat e de embeddings | nenhuma |
| `ollama-init` | Baixa os modelos que faltam e termina | nenhuma |
| `chroma` | Banco vetorial persistente | nenhuma |
| `postgres` | Metadados dos documentos, conversas e mensagens | nenhuma |
| `searxng` | Busca na internet, usada só quando a pessoa clica no botão | nenhuma |

Os containers conversam pelos nomes dos serviços na rede do Docker.

Fluxo de um PDF: envio → validação → arquivo em `/data/documents/<id>.pdf` → extração do texto por
página → trechos de `CHUNK_SIZE` caracteres com `CHUNK_OVERLAP` de sobreposição → embeddings
(`search_document: ...`) → ChromaDB (coleção `chunks-<modelo>`) → situação **pronto**.

Fluxo de uma pergunta: embedding da pergunta (`search_query: ...`) → `RETRIEVAL_TOP_K` trechos mais
próximos dos documentos escolhidos → contexto entre `<documentos>` → modelo de chat → eventos
`conversation`, `sources`, `thinking`, `token`, `done` ou `error` (Server-Sent Events). A pergunta é
gravada na conversa antes do streaming e a resposta no fim (com as fontes, com o erro ou, se a pessoa
parar, com o que já tinha chegado). O histórico enviado ao modelo são as últimas
`HISTORY_MAX_MESSAGES` mensagens concluídas da conversa, lidas do banco. Se o modelo disser que não
encontrou a resposta, o evento `not_found` vem antes do `done`.

Fluxo da busca na internet (só com o clique, `web_search: true`): evento `searching` → a pergunta vai ao
SearXNG → o backend lê o texto das primeiras `WEB_SEARCH_MAX_RESULTS` páginas (recusando endereços
internos e cortando em `WEB_PAGE_MAX_CHARS` caracteres; sem texto, usa o resumo do buscador) → contexto
entre `<resultados_web>`, sem os PDFs e sem o histórico → modelo de chat → resposta com fontes `web`.

## Tecnologias

| Parte | Tecnologias |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, [`@celke/kole-react`](https://www.npmjs.com/package/@celke/kole-react), nginx |
| Backend | Python 3.13, FastAPI, Pydantic, PyMuPDF, LangChain Text Splitters, cliente oficial do Ollama, cliente do ChromaDB, psycopg 3 |
| IA | Ollama 0.40, `qwen3:4b` (chat), `nomic-embed-text` (embeddings) |
| Banco vetorial | ChromaDB 1.5.9 |
| Banco de dados | PostgreSQL 18.6 |
| Testes | pytest, Ruff, Vitest, `tsc` |
| Busca na internet | SearXNG, trafilatura |
| Infraestrutura | Docker Compose |

## Requisitos

- **Docker** com o **Docker Compose**: Docker Desktop (Windows e macOS) ou Docker Engine com o plugin
  Compose (Linux).
- **Git** para clonar (ou baixe o ZIP pelo GitHub).
- **Memória:** 8 GB de RAM livres para o Docker (o `qwen3:4b` usa cerca de 4 GB). No macOS, ajuste em
  *Settings → Resources* do Docker Desktop. No Windows com WSL2, o Docker usa por padrão metade da RAM
  e o limite fica no arquivo `.wslconfig` (veja [Problemas comuns](#problemas-comuns)).
- **Windows:** Windows 10 ou 11 com o Docker Desktop no modo WSL2 (o padrão). Os comandos do README
  funcionam no PowerShell, exceto onde há um bloco próprio para ele.
- **Disco:** cerca de 6 GB (imagens e modelos).
- **Internet na primeira execução:** para baixar as imagens e os modelos. Depois disso, a aplicação
  funciona sem internet; só o botão **Pesquisar na internet** precisa de conexão.

## Executar com Docker

**1. Clonar o repositório**

```bash
git clone <url-do-repositório> celke-ia-local
cd celke-ia-local
```

**2. (Opcional) Criar o `.env`** para mudar porta, modelos ou limites. Sem ele, valem os padrões, e os
scripts do passo 3 criam o arquivo com uma senha aleatória para o PostgreSQL (`POSTGRES_PASSWORD`).

```bash
cp .env.example .env          # Linux e macOS
copy .env.example .env        # Windows (PowerShell ou cmd)
```

Guarde o `.env`: o PostgreSQL grava a senha na primeira subida, e uma senha nova não abre o banco antigo
(veja [Problemas comuns](#problemas-comuns)).

**3. Subir tudo**

Linux e macOS:

```bash
./scripts/iniciar.sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

O script confere o Docker, constrói as imagens, sobe os serviços, espera o `ollama-init` baixar os
modelos que faltam (cerca de 3 GB, só na primeira vez), confere a API e mostra o endereço. Pode rodar de
novo quantas vezes quiser: o que já existe não é baixado de novo.

Sem o script, o mesmo resultado em qualquer sistema, desde que o `.env` tenha `POSTGRES_PASSWORD` (sem
senha o `postgres` não sobe) e `SEARXNG_SECRET` preenchidos:

```bash
docker compose up -d --build
docker compose logs -f ollama-init      # acompanha o download; Ctrl+C quando aparecer "Modelos prontos."
```

**4. Acessar**

| Endereço | O quê |
|---|---|
| http://localhost:8090 | Aplicação |
| http://localhost:8090/api/docs | Documentação da API (Swagger) |
| http://localhost:8090/api/health | Saúde da API |

**5. Parar**

```bash
docker compose stop        # para e mantém tudo
docker compose start       # volta a rodar
```

## Usar a aplicação

1. Em **Status**, confira se todos os serviços estão verdes. Se algum modelo aparecer como ausente,
   o download ainda não terminou (`docker compose logs -f ollama-init`).
2. Em **Documentos**, escolha um ou mais PDFs e clique em **Enviar**. A tabela atualiza sozinha até a
   situação ficar **Pronto**. PDFs com erro mostram o motivo e podem ser reprocessados.
3. Em **Chat** (ou no ícone de conversa da linha do documento), escolha os documentos, um a um ou com
   **Selecionar todos**, e pergunte. Uma conversa reaberta começa sem documentos selecionados.
   A primeira pergunta demora mais: o modelo é carregado na memória. Enquanto o modelo raciocina,
   aparece "Analisando os trechos dos documentos…"; depois a resposta chega aos poucos.
4. Abra **fontes** abaixo da resposta para ver de qual documento e página veio cada trecho.
   Se os documentos não tiverem a resposta, clique em **Pesquisar na internet**: a mesma pergunta é
   respondida com páginas da web, e as fontes viram links. Confira as informações nos sites.
5. A conversa é salva a cada pergunta. **Conversas** lista as anteriores (a mais recente primeiro),
   **Nova conversa** começa outra e **Excluir** apaga a conversa aberta (os documentos continuam).

Para testar sem o navegador:

```bash
curl -F "file=@meu-arquivo.pdf;type=application/pdf" http://localhost:8090/api/documents
curl http://localhost:8090/api/documents
curl -N -X POST http://localhost:8090/api/chat -H "Content-Type: application/json" \
  -d '{"question": "Sobre o que é o documento?", "document_ids": ["<id>"]}'
# o primeiro evento traz o id da conversa; a próxima pergunta continua nela:
curl -N -X POST http://localhost:8090/api/chat -H "Content-Type: application/json" \
  -d '{"question": "Resuma em uma frase.", "document_ids": ["<id>"], "conversation_id": "<id-da-conversa>"}'
curl http://localhost:8090/api/conversations                     # conversas
curl http://localhost:8090/api/conversations/<id-da-conversa>    # mensagens com as fontes
```

No Windows PowerShell, `curl` é outro comando (apelido de `Invoke-WebRequest`) e as aspas do JSON se
perdem na linha de comando. Use `curl.exe` e envie a pergunta por um arquivo:

```powershell
curl.exe -F "file=@meu-arquivo.pdf;type=application/pdf" http://localhost:8090/api/documents
curl.exe http://localhost:8090/api/documents
@{ question = 'Sobre o que é o documento?'; document_ids = @('<id>') } | ConvertTo-Json |
  ForEach-Object { [IO.File]::WriteAllText("$PWD\pergunta.json", $_) }
curl.exe -N -X POST http://localhost:8090/api/chat -H "Content-Type: application/json" -d "@pergunta.json"
```

## Configuração e troca de modelos

As variáveis ficam no `.env` (modelo completo em [`.env.example`](.env.example)). Depois de mudar,
execute `docker compose up -d` (ou o script de novo).

| Variável | Padrão | Para quê |
|---|---|---|
| `APP_PORT` | `8090` | Porta da aplicação no seu computador |
| `APP_BIND` | `127.0.0.1` | `0.0.0.0` abre para a rede local (ver [Segurança](#segurança)) |
| `COMPOSE_FILE` | (vazio) | Liga a GPU NVIDIA em todos os comandos (ver abaixo) |
| `CHAT_MODEL` | `qwen3:4b` | Modelo de chat do Ollama |
| `CHAT_THINK` | `auto` | `auto` separa o raciocínio da resposta quando o modelo raciocina |
| `CHAT_NUM_CTX` | `8192` | Janela de contexto (tokens); mais contexto, mais memória |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `EMBEDDING_DOCUMENT_PREFIX` / `EMBEDDING_QUERY_PREFIX` | `search_document: ` / `search_query: ` | Prefixos do nomic; vazios para outros modelos |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` | Tamanho e sobreposição dos trechos (caracteres) |
| `RETRIEVAL_TOP_K` | `5` | Trechos enviados ao modelo por pergunta |
| `HISTORY_MAX_MESSAGES` | `6` | Mensagens anteriores da conversa enviadas junto com a pergunta |
| `POSTGRES_PASSWORD` | (vazio) | Senha do PostgreSQL, obrigatória; os scripts geram uma aleatória. Vale só na criação do volume |
| `POSTGRES_DB` / `POSTGRES_USER` | `celke_ia_local` / `celke` | Nome do banco e do usuário (também só na criação do volume) |
| `SEARXNG_SECRET` | (vazio) | Chave interna do SearXNG, obrigatória; os scripts geram uma aleatória |
| `WEB_SEARCH_TIMEOUT_SECONDS` | `15` | Tempo máximo da busca e da leitura de cada página |
| `WEB_SEARCH_MAX_RESULTS` | `3` | Páginas lidas por pesquisa |
| `WEB_PAGE_MAX_CHARS` | `2000` | Texto de cada página enviado ao modelo; mais texto, mais memória |
| `MAX_UPLOAD_MB` | `25` | Tamanho máximo de cada PDF |
| `OLLAMA_KEEP_ALIVE` | `30m` | Tempo que o modelo fica na memória depois da última pergunta |

**Trocar o modelo de chat** (por exemplo `qwen3:8b`, que exige mais memória): mude `CHAT_MODEL` e rode
o script de inicialização de novo. O `ollama-init` baixa o novo modelo; o antigo continua no volume (apague com
`docker compose exec ollama ollama rm qwen3:4b`).

**Trocar o modelo de embeddings:** mude `EMBEDDING_MODEL` (e os prefixos). Cada modelo de embeddings tem
a própria coleção no ChromaDB, porque vetores de modelos diferentes não podem ser comparados. Os
documentos já enviados aparecem como **Reprocessar** e saem do chat até serem reprocessados.

**GPU NVIDIA.** No Windows, basta o driver NVIDIA atualizado e o Docker Desktop com WSL2, sem instalar
nada dentro do WSL. No Linux, é preciso o
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

Para valer em todos os comandos, inclusive nos scripts, acrescente uma linha ao `.env` e rode o script
de inicialização de novo:

```bash
COMPOSE_FILE=compose.yaml;compose.gpu.yaml   # Windows
COMPOSE_FILE=compose.yaml:compose.gpu.yaml   # Linux
```

Para conferir, faça uma pergunta e rode `docker compose exec ollama ollama ps`: a coluna `PROCESSOR`
deve mostrar `100% GPU`. Em computadores sem GPU NVIDIA, o `ollama` não sobe com essa linha no `.env`.

## Testes

Os testes rodam em containers; não é preciso Python nem Node instalados.

```bash
# Backend: Ruff (lint e formatação) e testes unitários. Não usam o Ollama nem baixam modelos;
# usam um PostgreSQL descartável em memória (serviço postgres-test), sem tocar no banco da aplicação.
docker compose --profile test run --rm --build backend-tests

# Frontend: verificação de tipos (tsc) e testes do Vitest
docker compose --profile test run --rm --build frontend-tests

# Integração: envio de PDF, indexação, pergunta ao modelo real, fontes, conversa gravada e exclusão.
# Precisa da stack no ar com os modelos baixados.
docker compose --profile test run --rm --build backend-tests pytest -m integration -v
```

| Conjunto | O que cobre |
|---|---|
| `tests/unit/test_pdf_and_chunker.py` | Extração por página, PDF sem texto, PDF corrompido, tamanho e sobreposição dos trechos |
| `tests/unit/test_documents_api.py` | Envio, validação (tipo, conteúdo, tamanho, duplicado, nome com caminho), processamento, erros, reprocessamento, exclusão sem afetar outros documentos, estado dos serviços |
| `tests/unit/test_chat.py` | Streaming, fontes, só os documentos escolhidos, sem contexto, histórico da conversa, raciocínio fora da resposta, erros do modelo |
| `tests/unit/test_conversations.py` | Conversa criada na primeira pergunta, mensagens e fontes gravadas, título, tentar de novo só após erro, resposta interrompida, exclusão, conversa depois de excluir o documento, importação do SQLite antigo |
| `tests/unit/test_ollama_service.py` | Modelo ausente, conexão recusada, timeout, memória insuficiente, raciocínio separado |
| `tests/unit/test_web_search.py` | Busca só quando pedida, só a pergunta enviada, páginas lidas e cortadas, endereços internos e redirecionamentos bloqueados, fontes web, `not_found`, erro e nova tentativa |
| `tests/integration/test_full_flow.py` | Fluxo completo com Ollama, ChromaDB e PostgreSQL reais |
| `frontend/src/services/sse.test.ts` | Leitura do streaming (blocos partidos, `\r\n`) |

## Comandos úteis

```bash
docker compose ps                         # situação dos containers
docker compose logs -f backend            # logs da API e do processamento dos PDFs
docker compose logs -f ollama ollama-init # logs do Ollama e do download dos modelos
docker compose logs --tail 100 frontend   # logs do nginx
docker compose logs postgres              # logs do banco de dados
docker compose logs searxng               # logs da busca na internet
docker compose exec postgres psql -U celke celke_ia_local   # console SQL (\dt lista as tabelas)
docker compose exec ollama ollama list    # modelos instalados
docker compose exec ollama ollama ps      # modelo carregado na memória agora
docker compose restart backend            # reinicia só a API
docker stats                              # memória e CPU de cada container
```

## Dados: preservar ou apagar

Os dados ficam em volumes do Docker e sobrevivem a `stop`, `down`, reinicialização do computador e
reconstrução das imagens:

| Volume | Conteúdo |
|---|---|
| `celke-ia-local_app-data` | PDFs enviados |
| `celke-ia-local_chroma-data` | Vetores e trechos indexados |
| `celke-ia-local_postgres-data` | Metadados dos documentos, conversas e mensagens |
| `celke-ia-local_ollama-models` | Modelos baixados |

```bash
docker compose down          # remove os containers e mantém os dados
docker compose down -v       # remove os containers e APAGA documentos, vetores, conversas e modelos
# apaga documentos e conversas, mantém os modelos (com os containers parados: docker compose down)
docker volume rm celke-ia-local_app-data celke-ia-local_chroma-data celke-ia-local_postgres-data
```

Cópia de segurança do banco e restauração:

```bash
docker compose exec -T postgres pg_dump -U celke celke_ia_local > backup.sql
docker compose exec -T postgres psql -U celke celke_ia_local < backup.sql
```

No Windows PowerShell, rode pelo `cmd`: o `<` não existe no PowerShell e, no 5.1, o `>` grava em UTF-16,
o que estraga o arquivo.

```powershell
cmd /c "docker compose exec -T postgres pg_dump -U celke celke_ia_local > backup.sql"
cmd /c "docker compose exec -T postgres psql -U celke celke_ia_local < backup.sql"
```

**Vindo de uma versão com SQLite:** na primeira subida com o PostgreSQL, o backend importa os documentos
do `/data/app.db` (os vetores no ChromaDB continuam valendo) e renomeia o arquivo para
`app.db.importado`, que fica como cópia de segurança.

## Atualizar o projeto

```bash
git pull
./scripts/iniciar.sh         # reconstrói as imagens e mantém os dados
# Windows: powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

O layout vem do pacote `@celke/kole-react` do npm (`"^0.1.0"` no `frontend/package.json`). Para trazer
uma versão nova da biblioteca, dentro de `frontend/`:

```bash
npm update @celke/kole-react      # versões compatíveis (0.1.x)
npm install @celke/kole-react@latest
```

O Dockerfile usa o `package-lock.json`: depois de atualizar, faça o commit dos dois arquivos e rode o
script de novo.

## Desenvolvimento

Para editar o frontend com recarga ao salvar (exige Node.js 24 só neste modo):

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d   # publica a API em 127.0.0.1:8000
cd frontend
npm install
npm run dev                                                 # http://localhost:5173
```

O Vite repassa `/api` para `http://localhost:8000` (outro endereço: `VITE_API_PROXY`). Depois de mudar
o backend, `docker compose up -d --build backend`.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| Modelo **ausente** em Status | O download não terminou ou falhou: `docker compose logs ollama-init`. Para tentar de novo: `docker compose up ollama-init` |
| "Ollama não tem memória suficiente" | Aumente a memória do Docker Desktop, feche outros programas ou use um modelo menor (`CHAT_MODEL=qwen3:1.7b`) |
| A primeira resposta demora ou dá timeout | O modelo está sendo carregado; tente de novo. Em CPU, respostas longas levam dezenas de segundos. Aumente `OLLAMA_TIMEOUT_SECONDS` se precisar |
| PDF com erro "não tem texto selecionável" | O PDF é uma imagem digitalizada. Esta versão não faz OCR |
| PDF com erro "processamento interrompido" | O backend reiniciou durante o processamento. Clique em **Reprocessar** |
| "Este PDF já foi enviado" | O mesmo arquivo (mesmo conteúdo) já está na lista |
| Porta 8090 ocupada | Defina outra no `.env` (`APP_PORT=8091`) |
| Windows: "Ollama não tem memória suficiente" ou containers encerrados por falta de memória | Crie `%UserProfile%\.wslconfig` com as linhas `[wsl2]` e `memory=8GB`, rode `wsl --shutdown` e reabra o Docker Desktop |
| Windows: "permission denied" ou "access a socket" ao publicar a porta | O Windows reservou a porta (`netsh interface ipv4 show excludedportrange protocol=tcp`). Defina outra em `APP_PORT` |
| Página não abre | `docker compose ps` (todos `healthy`?) e `docker compose logs backend frontend` |
| Mudou o modelo de embeddings e os documentos sumiram do chat | Reprocesse cada documento em **Documentos** |
| `postgres` não sobe: "superuser password is not specified" | Falta `POSTGRES_PASSWORD` no `.env`. Rode o script de inicialização (cria a senha) ou preencha à mão |
| Backend reinicia em loop com "password authentication failed" | O `.env` tem uma senha diferente da usada na criação do banco. Volte a senha antiga ou, para começar do zero, apague o volume `celke-ia-local_postgres-data` (perde documentos e conversas) |
| "A busca na internet não está disponível" | Sem conexão ou SearXNG fora do ar: confira **Status** e `docker compose logs searxng`. O chat com os documentos continua funcionando |
| A busca não traz resultados | Os buscadores podem limitar pedidos automáticos. Espere alguns minutos e tente de novo |
| "O banco de dados (PostgreSQL) não está respondendo" | `docker compose ps postgres` e `docker compose logs postgres` |

## Hardware e limitações

- Sem GPU, o `qwen3:4b` gera cerca de 10 a 20 palavras por segundo num processador recente de 8 núcleos;
  computadores mais simples são mais lentos. Com GPU NVIDIA, a resposta é várias vezes mais rápida.
- O `qwen3:4b` raciocina antes de responder; a resposta começa depois de alguns segundos.
- Não há OCR: PDFs digitalizados como imagem não são lidos.
- A busca na internet soma alguns segundos à resposta e lê só o começo de cada página, então a resposta
  pode não estar no trecho lido. O aviso de "não encontrei" depende do que o modelo responde; se ele
  errar, as demais respostas continuam com o botão de pesquisa.
- Só a última resposta, quando dá erro, pode ser gerada de novo; as conversas não têm busca nem renomeação.
- Um PDF é processado por vez; os demais aguardam na fila.

## Segurança

A aplicação foi feita para uso local, num computador pessoal. **Não a publique na internet como está:**
não há login, e qualquer pessoa com acesso ao endereço pode enviar, ler e apagar documentos.

- Só a porta do frontend é publicada, e apenas em `127.0.0.1`. O Ollama, o ChromaDB, o PostgreSQL e o
  SearXNG não têm porta no host.
- A senha do PostgreSQL fica só no `.env` (fora do git), gerada aleatoriamente pelos scripts.
- `APP_BIND=0.0.0.0` abre a aplicação para a rede local; use só em rede confiável.
- Os arquivos são gravados com um identificador interno (o nome enviado nunca vira caminho), com limite
  de tamanho e verificação do conteúdo.
- O texto dos PDFs vai ao modelo como dado, e o prompt de sistema manda ignorar instruções que apareçam
  nele. O modelo não executa comandos nem acessa arquivos.
- **Busca na internet:** a pergunta vai aos buscadores (DuckDuckGo, Brave, Mojeek e Wikipedia) por meio
  do SearXNG, então não pesquise dados sigilosos. O conteúdo dos PDFs nunca é enviado. O texto das
  páginas é dado não confiável, e o backend só abre endereços públicos em http(s), nas portas 80 e 443,
  conferindo cada redirecionamento, para que um site não o faça acessar os containers ou a rede local.
- O CORS fica desligado: o navegador acessa a API pelo nginx, na mesma origem.
- Os containers do backend rodam com usuário sem privilégios; nenhum usa modo privilegiado.

## Estrutura do projeto

```
backend/     API FastAPI: app/api (rotas), core (configuração, erros), schemas, services
             (PDF, trechos, Ollama, documentos, conversas, RAG), repositories (PostgreSQL,
             ChromaDB) e tests/
frontend/    React + Vite com o Kole React: layouts, pages, services (API e streaming), hooks; nginx
searxng/     Configuração da busca na internet
scripts/     iniciar.sh (Linux e macOS) e iniciar.ps1 (Windows)
docs/        Prompts para recriar o projeto do zero
compose.yaml           Serviços, volumes e perfis de teste
compose.gpu.yaml       GPU NVIDIA para o Ollama
compose.dev.yaml       API publicada para o Vite em desenvolvimento
```

## Prompts para recriar o projeto

[`docs/prompts-iniciais/`](docs/prompts-iniciais/README.md) tem os prompts que recriam este projeto do zero com
um agente de IA (Claude Code ou outro com acesso ao terminal), com o conteúdo exato dos arquivos, a escolha do
modelo pela capacidade do computador e orientações do que fazer em cada etapa.

## Licença

MIT. Veja [LICENSE.txt](LICENSE.txt).
``````

`CLAUDE.md`:

``````markdown
# Guia para agentes de IA e desenvolvedores

Convenções deste repositório. Leia o `README.md` antes de começar: ele descreve a arquitetura, os
comandos e as variáveis de ambiente.

| Pasta | Projeto | Stack |
|---|---|---|
| `backend/` | API, processamento dos PDFs, RAG e conversas | Python 3.13, FastAPI, Pydantic, PyMuPDF, Ollama, ChromaDB, PostgreSQL (psycopg 3) |
| `frontend/` | Chat, documentos e status | React 19, TypeScript, Vite, React Router, `@celke/kole-react` |
| raiz | Docker Compose, scripts de inicialização | Docker Compose |
| `docs/prompts-iniciais/` | Prompts usados para criar o projeto do zero | Markdown |

## Branches e commits

- `main` = versão estável, `homolog` = homologação. Trabalhe numa branch própria a partir de `homolog`
  (`feature/nome` ou `fix/nome`) e entregue por Pull Request para `homolog`; a promoção
  `homolog → main` também é por Pull Request ou merge.
- Commit, push e Pull Request só quando o desenvolvedor pedir. Mensagens no padrão Conventional
  Commits em português, **sem** coautoria nem menção a ferramenta de IA.

## Regras gerais

- Tudo roda no Docker. Não exija Python nem Node instalados para executar ou testar.
- Interface, mensagens de erro e documentação em português do Brasil; nomes de classes, funções,
  variáveis e arquivos em inglês.
- Nada de segredos no código, no compose ou na documentação. Configuração só por variável de ambiente
  (com padrão no `compose.yaml` e explicação no `.env.example`).
- Só a porta do frontend é publicada, em `127.0.0.1`. Não publique as portas do Ollama, do ChromaDB, do
  PostgreSQL nem do backend no `compose.yaml` (a do backend existe só no `compose.dev.yaml`).
- A senha do PostgreSQL (`POSTGRES_PASSWORD`) não tem padrão: vem do `.env`, que os `scripts/iniciar.*`
  criam com uma senha aleatória.
- `SEARXNG_SECRET` segue a mesma regra. A busca na internet só acontece com o clique da pessoa: nunca
  pesquise automaticamente nem envie conteúdo dos PDFs ao buscador.
- Mudou uma variável? Atualize `config.py`, `compose.yaml`, `.env.example` e a tabela do README juntos.

## Backend

- Camadas: `api/` (rotas finas, sem regra de negócio) → `services/` (regras) → `repositories/`
  (PostgreSQL e ChromaDB). Os objetos compartilhados são criados em `core/container.py`.
- Erros de negócio herdam de `AppError` (`core/errors.py`) e viram
  `{"erro": {"codigo", "mensagem"}}` com o código HTTP da classe. Mensagens para o usuário, em
  português e com a ação a tomar.
- Metadados dos documentos, conversas e mensagens no PostgreSQL (pool em
  `repositories/database.py`, esquema idempotente criado na inicialização; SQL sempre com parâmetros
  `%s` ou `psycopg.sql`); trechos e vetores no ChromaDB, uma coleção por modelo de embeddings. Excluir
  um documento remove os vetores primeiro, depois o arquivo e o registro; as conversas continuam.
- O chat grava a pergunta antes do streaming e a resposta no fim (com erro ou interrompida). O
  histórico enviado ao modelo vem do banco, nunca do navegador.
- O texto das páginas da web também é dado não confiável (vai dentro de `<resultados_web>`), e
  `services/web_search.py` só acessa endereços públicos.
- O conteúdo dos PDFs é dado não confiável: vai ao modelo dentro de `<documentos>`, nunca como
  instrução. O modelo não executa comandos nem acessa arquivos.
- O chat responde em Server-Sent Events: `conversation`, `sources`, `thinking` (uma vez), `token`,
  `done` ou `error`; na busca na internet, também `searching` antes de `sources`; `not_found` antes do
  `done` quando os documentos não têm a resposta.
  Qualquer evento novo precisa ser tratado também em `frontend/src/services/sse.ts`.
- Testes unitários usam os dublês de `tests/fakes.py` e não dependem do Ollama; o banco é o serviço
  `postgres-test` (em memória, tabelas limpas antes de cada teste). Testes que usam o Ollama e o
  ChromaDB reais ficam em `tests/integration/` com `@pytest.mark.integration`.
- Antes de entregar: `docker compose --profile test run --rm --build backend-tests` (Ruff e pytest).

## Frontend

- Use os componentes reais do `@celke/kole-react` (veja o README do pacote e os tipos em
  `node_modules/@celke/kole-react/dist`). Não invente componentes nem props. As props do Kole são em
  português (`rotulo`, `aoMudar`, `valor`) e ficam como estão.
- Estilos próprios só em `src/styles.css`, com as variáveis do tema do Kole (`--surface`, `--t3`,
  `--pri`, `--err-fg`…); nada de cor fixa, para o tema escuro continuar funcionando.
- Ícones pelo nome: os que não vêm registrados no Kole são registrados em `src/main.tsx` com
  `registrarIcones`.
- Toda chamada à API passa por `src/services/api.ts`; o envio de arquivo usa `XMLHttpRequest` para
  mostrar o progresso.
- Antes de entregar: `docker compose --profile test run --rm --build frontend-tests` (tsc e Vitest).

## Prompts do tutorial

`docs/prompts-iniciais/` recria o projeto do zero. Mudou algo que um prompt cria? Atualize o prompt da etapa
correspondente no mesmo commit. Os prompts são escritos como originais: sem datas, sem histórico de
correções e sem caminhos de outros projetos.
``````

Copie a pasta de prompts para `docs/prompts-iniciais/`, sem o `progresso.md`.

## Verificação

```bash
docker compose config -q && echo ok
docker compose ps
git status --short    # .env não aparece
```

Confira que os links internos do README existem (`.env.example`, `LICENSE.txt`, `docs/prompts-iniciais/README.md`).

## Depois de executar

```bash
git add README.md CLAUDE.md docs/prompts-iniciais
git commit -m "docs: adiciona o README, o guia para agentes e os prompts iniciais"
git branch homolog
```

Mensagens sem `Co-Authored-By` nem menção a ferramenta de IA. Não faça push.

## Orientação ao terminar

Mostre, trocando os marcadores:

> **O Celke IA Local está pronto em http://localhost:<porta>** com o modelo `<modelo>`.
>
> **Agora é com você, no navegador:**
> 1. Em **Status**, confira se tudo está verde.
> 2. Em **Documentos**, envie um PDF com texto e espere a situação **Pronto**. PDF digitalizado como imagem não funciona.
> 3. Em **Chat**, selecione o documento e faça uma pergunta. A primeira resposta demora mais, porque o modelo é carregado.
> 4. Abra **fontes** abaixo da resposta para ver documento e página.
> 5. Pergunte algo que não está no PDF e clique em **Pesquisar na internet**. Só a pergunta sai do computador.
>
> **Comandos úteis:** parar com `docker compose stop`; voltar com `docker compose start`; apagar tudo, inclusive documentos
> e modelos, com `docker compose down -v`.
>
> **Trocar o modelo:** mude `CHAT_MODEL` no `.env` e rode o script de inicialização de novo.
>
> **Enviar ao GitHub (opcional):** crie um repositório vazio e rode `git remote add origin <url>` e
> `git push -u origin main homolog`.
