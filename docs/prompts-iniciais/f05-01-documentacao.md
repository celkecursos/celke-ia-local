# Documentação e entrega

**Etapa:** 5 de 5
**Requer:** etapa 4

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar o README e o guia para agentes de IA e fazer a entrega final.
> **O que você precisa fazer:** nada por enquanto. No final, mostro como testar no navegador.

## Prompt

Crie a documentação do **Celke IA Local**, deixe os prompts no projeto e crie a branch de homologação. Os arquivos de
`docs/prompts` são os mesmos passos em texto, para o tutorial, e `docs/gerador-prompts` mantém estes prompts atualizados:
crie-os como estão, sem executá-los.

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
modelo pela capacidade do computador e orientações do que fazer em cada etapa. Essa pasta basta sozinha: não
precisa de nenhum outro arquivo do projeto.
[`docs/prompts/`](docs/prompts/README.md) descreve as mesmas etapas em texto, para o tutorial.

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
| `docs/prompts-iniciais/` | Prompts que recriam o projeto do zero, sozinhos, com o conteúdo exato dos arquivos (gerados) | Markdown |
| `docs/prompts/` | As mesmas etapas descritas em texto, para o tutorial | Markdown |
| `docs/gerador-prompts/` | Gera e confere `docs/prompts-iniciais/` | Python |

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

`docs/prompts/` recria o projeto do zero. Mudou algo que um prompt cria? Atualize o prompt da etapa
correspondente no mesmo commit. Os prompts são escritos como originais: sem datas, sem histórico de
correções e sem caminhos de outros projetos.

`docs/prompts-iniciais/` é gerado: não edite à mão. O texto das orientações fica em
`docs/gerador-prompts/gerar_prompts.py`, e o conteúdo dos arquivos vem do próprio projeto. Mudou um arquivo?
Gere de novo no mesmo commit e confira (o segundo comando precisa terminar com `diferentes 0`):

```bash
docker run --rm -v "${PWD}:/repo" -w /repo python:3.13-slim python docs/gerador-prompts/gerar_prompts.py
docker run --rm -v "${PWD}:/repo" -w /repo python:3.13-slim python docs/gerador-prompts/testar_prompts.py
```
``````

`docs/gerador-prompts/gerar_prompts.py`:

``````python
"""Gera prompts-iniciais/ com o conteúdo atual dos arquivos do projeto. Ver "Prompts do tutorial" no CLAUDE.md."""
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "prompts-iniciais"
# Fora dos prompts: o que é gerado ou só existe neste computador.
SKIP_DIRS = {".git", ".claude", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "node_modules", "dist",
             "prompts-iniciais"}
SKIP_FILES = {".env", ".DS_Store", "configuracao.md", "progresso.md"}
FENCE = "`" * 6
LANG = {".py": "python", ".ts": "ts", ".tsx": "tsx", ".css": "css", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".md": "markdown", ".sh": "sh", ".ps1": "powershell", ".html": "html", ".svg": "xml", ".toml": "toml",
        ".txt": "text", ".template": "nginx"}


def project_files():
    found = []
    for folder, dirs, names in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found += [(Path(folder) / n).relative_to(REPO).as_posix() for n in names if n not in SKIP_FILES]
    return sorted(found)


FILES = project_files()


def content(path):
    text = (REPO / path).read_bytes().decode("utf-8").replace("\r\n", "\n")
    # Valores de quem gerou viram marcadores, trocados por quem recria.
    if path == "README.md":
        text = re.sub(r"git clone \S+ celke-ia-local", "git clone <url-do-repositório> celke-ia-local", text)
    if path == "LICENSE.txt":
        text = re.sub(r"Copyright \(c\) .*", "Copyright (c) <ano> <titular-da-licenca>", text, count=1)
    assert FENCE not in text, path
    return text


def block(path):
    name = Path(path).name
    lang = LANG.get(Path(path).suffix, "text")
    if name == "Dockerfile":
        lang = "dockerfile"
    elif name.startswith("."):
        lang = "text"
    return f"`{path}`:\n\n{FENCE}{lang}\n{content(path)}{'' if content(path).endswith(chr(10)) else chr(10)}{FENCE}\n"


def blocks(paths):
    empty = [p for p in paths if not content(p)]
    full = [p for p in paths if content(p)]
    text = "\n".join(block(p) for p in full)
    if empty:
        text += "\nCrie também estes arquivos **vazios**:\n\n" + "\n".join(f"- `{p}`" for p in empty) + "\n"
    return text


ROOT = [".gitignore", ".gitattributes", ".dockerignore", ".env.example", "compose.yaml", "compose.gpu.yaml",
        "compose.dev.yaml", "searxng/settings.yml", "scripts/iniciar.sh", "scripts/iniciar.ps1"]
BACKEND = [f for f in FILES if f.startswith("backend/")]
FRONTEND = [f for f in FILES if f.startswith("frontend/") and f != "frontend/package-lock.json"]
DOCS = ["README.md", "CLAUDE.md"] + [f for f in FILES if f.startswith("docs/")]
accounted = set(ROOT + BACKEND + FRONTEND + DOCS + ["LICENSE.txt", "frontend/package-lock.json"])
assert set(FILES) == accounted, set(FILES) ^ accounted

RULES = """Regras desta etapa:

- Crie os arquivos com **exatamente** o conteúdo indicado, sem melhorar nem reformatar. O conteúdo já foi
  testado junto; uma alteração aqui quebra outra etapa.
- Não pergunte nada ao usuário: as decisões estão neste prompt e em `docs/configuracao.md`.
- Mostre ao usuário as seções **Orientação** (antes de começar e ao terminar), com as suas palavras só onde
  houver marcador a trocar. Se o terminal não permitir mostrar agora, inclua no seu relatório final.
- Rode tudo o que está em **Verificação** e corrija o que falhar antes de terminar.
- Nunca mostre o valor de `POSTGRES_PASSWORD` nem de `SEARXNG_SECRET`.
"""

F00 = f"""# Preparação do computador e escolha do modelo de IA

**Etapa:** 0 de 5
**Quem executa:** a sessão principal do agente, porque esta é a única etapa com pergunta ao usuário.

## Orientação antes de começar

> **O que vai acontecer agora:** vou conferir o seu computador e recomendar o modelo de IA.
> **O que você precisa fazer:** selecionar o modelo de IA e, se o Git ainda não estiver configurado, preencher nome e
> e-mail. O resto é automático.
> **Importante:** não instale o Ollama no computador. Ele roda dentro do Docker e é configurado pelo projeto.

## Prompt

Você vai preparar a criação do **Celke IA Local**: chatbot que responde perguntas sobre PDFs com um modelo
de IA rodando no computador da pessoa (React com `@celke/kole-react`, FastAPI, Ollama 0.40, ChromaDB,
PostgreSQL, SearXNG e Docker Compose). Faça os passos na ordem. Só os passos 4 e 6 fazem pergunta.

### 1. Ferramentas

Confira `git --version`, `docker --version`, `docker compose version` e `docker info`. Se algo faltar, **pare**
e mostre só a orientação do caso. Depois de resolver, a pessoa executa o mesmo prompt de novo.

| Caso | Mostre ao usuário |
|---|---|
| Git ausente | "Instale o Git em https://git-scm.com/downloads, abra um terminal novo e execute este prompt de novo." |
| Docker ausente, Windows | "Instale o Docker Desktop em https://www.docker.com/products/docker-desktop/ e mantenha a opção WSL 2 marcada. Reinicie o computador se ele pedir, abra o Docker Desktop, espere aparecer *Engine running* e execute este prompt de novo." |
| Docker ausente, macOS | "Instale o Docker Desktop em https://www.docker.com/products/docker-desktop/, abra o programa, espere aparecer *Engine running* e execute este prompt de novo." |
| Docker ausente, Linux | "Instale o Docker Engine com o plugin Compose: https://docs.docker.com/engine/install/. Depois rode `sudo usermod -aG docker $USER`, entre de novo na sessão e execute este prompt de novo." |
| `docker info` falhou | "O Docker está instalado, mas não está rodando. Abra o Docker Desktop (no Linux, `sudo systemctl start docker`), espere iniciar e execute este prompt de novo." |

### 2. Projeto existente

Se a pasta atual já for um repositório com commits e não houver `progresso.md` na pasta de prompts, **pare**:
"Esta pasta já tem um projeto. Crie uma pasta vazia, coloque `prompts-iniciais` dentro dela e execute de novo."

Rode `docker ps -a --filter label=com.docker.compose.project=celke-ia-local --format "{{{{.Names}}}}"` e
`docker volume ls --filter label=com.docker.compose.project=celke-ia-local --format "{{{{.Name}}}}"`. Se
listarem algo, **pare**: nunca apague esses dados por conta própria. Mostre: "Este computador já tem uma
instalação do Celke IA Local. Para substituí-la **apagando documentos e conversas**, rode, na pasta dela,
`docker compose down -v`. Depois execute este prompt de novo."

### 3. Capacidade do computador

Colete os dados sem perguntar nada:

- **Windows (PowerShell):** `(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB`,
  `(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors` e o espaço livre do disco da pasta atual com
  `Get-PSDrive`.
- **Linux:** `free -g`, `nproc`, `df -BG .`.
- **macOS:** `sysctl -n hw.memsize hw.ncpu`, `df -g .`.
- **Memória e processadores que o Docker enxerga** (é o que vale): `docker info --format "{{{{.MemTotal}}}} {{{{.NCPU}}}}"`
  (`MemTotal` em bytes). No Windows com WSL 2, o padrão costuma ser metade da RAM.
- **GPU:** `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader`. Só se responder, confirme que o
  Docker a alcança: `docker run --rm --gpus all --entrypoint nvidia-smi ollama/ollama:0.40.13 -L`.
  A GPU só conta se os dois funcionarem. AMD, Intel e Apple Silicon contam como **sem GPU**: este projeto só
  liga GPU NVIDIA, e o Docker no macOS não usa a GPU do Mac.

### 4. Escolha do modelo

Modelos do Ollama, da família `qwen3` (todos separam o raciocínio da resposta). Memória é o que o modelo de
chat e o de embeddings ocupam juntos, com a janela de contexto de 8192 tokens:

| Modelo | Download | Memória | Para quem | Medição de referência |
|---|---|---|---|---|
| `qwen3:1.7b` | 1,4 GB | cerca de 3 GB | Computador com pouca memória; respostas mais simples | estimativa |
| `qwen3:4b` | 2,5 GB | 4,3 GB | Padrão do projeto; bom equilíbrio | medido; RTX 3060 |
| `qwen3:8b` | 5,2 GB | 6,7 GB | Respostas melhores; pede GPU ou bastante memória | medido; RTX 3060, 54 tokens/s |
| `qwen3:14b` | 9,3 GB | 10,4 GB | Ainda melhor; pede GPU de 12 GB | medido; RTX 3060, 31 tokens/s |
| `qwen3:30b` | 18,6 GB | cerca de 20 GB | Máximo desta lista; pede GPU de 24 GB | estimativa |

**Modelo recomendado.** Use a primeira linha que couber, de cima para baixo:

| Situação | Recomendado |
|---|---|
| GPU com 24 GB ou mais | `qwen3:30b` |
| GPU com 12 GB ou mais | `qwen3:14b` |
| GPU com 8 GB ou mais | `qwen3:8b` |
| GPU com 6 GB ou mais | `qwen3:4b` |
| Sem GPU, Docker com 12 GB ou mais e 12 processadores ou mais | `qwen3:8b` |
| Sem GPU, Docker com 6,5 GB ou mais | `qwen3:4b` |
| Qualquer outro caso | `qwen3:1.7b` |

Depois, confira o disco: o espaço livre precisa ser de pelo menos 8 GB mais o download do modelo. Se não for,
desça para o maior modelo que couber. Se nem o `qwen3:1.7b` couber, **pare** e diga quantos GB a pessoa precisa
liberar.

**Pergunta.** Mostre os dados encontrados e faça **uma única pergunta**, com a ferramenta de pergunta se houver, para a
pessoa selecionar uma opção ou preencher o nome de outro modelo. Espere a resposta. Ofereça sempre três opções: a **recomendada** (primeira, marcada como recomendada), a imediatamente **inferior** e
a imediatamente **superior**. Nos extremos da tabela, complete com a vizinha seguinte. Na opção superior, diga o
risco quando a memória não for suficiente: "pode ficar muito lento ou não carregar". Modelo:

> **Seu computador:** <RAM> GB de RAM, <memória do Docker> GB para o Docker, <processadores> processadores,
> <GPU e memória, ou "sem GPU NVIDIA">, <espaço livre> GB livres.
>
> **Qual modelo de IA você quer usar?** Ele pode ser trocado depois.
> 1. `<recomendado>` (**recomendado**): <motivo em uma frase, com a memória que ele usa> Download de <tamanho>.
> 2. `<inferior>`: mais leve e rápido, com respostas mais simples. Download de <tamanho>.
> 3. `<superior>`: respostas melhores. <risco, se houver> Download de <tamanho>.
>
> Responda 1, 2 ou 3 (ou o nome de outro modelo do Ollama). Sem preferência? Escolha a 1.

Se a pessoa informar outro modelo, aceite e avise que ele não foi testado com o projeto. O modelo de embeddings
não é pergunta: é sempre `nomic-embed-text`.

Se a memória do Docker no Windows for menor que a necessária e a RAM do computador comportar o modelo, acrescente
esta orientação, sem alterar nada por conta própria: "Para dar mais memória ao Docker, crie
`%UserProfile%\\.wslconfig` com as linhas `[wsl2]` e `memory=8GB`, rode `wsl --shutdown` e abra o Docker Desktop."

### 5. Decisões automáticas (não pergunte)

- **GPU:** ligada se o passo 3 confirmou a GPU.
- **Porta:** `8090`. Se estiver ocupada, use a primeira livre de `8091` a `8099`.
- **Git:** se a pasta não for um repositório, `git init -b main`. Acrescente `/<pasta de prompts>/` em
  `.git/info/exclude`.
- **Licença:** MIT, com `git config user.name` como titular e o ano atual.

### 6. Nome e e-mail do Git

Confira `git config user.name` e `git config user.email`. Se os dois tiverem valor, não pergunte nada. Se faltar algum,
faça a pergunta abaixo, com a ferramenta de pergunta se houver, pedindo só o que falta, e espere a resposta:

> **Qual nome e e-mail devem aparecer nos commits deste projeto?** O nome também vai na licença. Preencha:
>
> - **Nome:**
> - **E-mail:**

Se o e-mail vier sem `@`, peça de novo. Grave com `git config user.name` e `git config user.email`, só neste repositório.

### 7. Arquivos

Crie o `.env` (UTF-8 sem BOM, com a sua ferramenta de escrita de arquivos), com duas chaves aleatórias diferentes de 48
caracteres hexadecimais. Gere cada uma com `od -An -N24 -tx1 /dev/urandom | tr -d ' \\n'` (Linux, macOS, Git Bash) ou
`$b = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object {{ $_.ToString('x2') }})`
(PowerShell):

```dotenv
POSTGRES_PASSWORD=<chave 1>
SEARXNG_SECRET=<chave 2>
CHAT_MODEL=<modelo escolhido>
```

Se a porta não for `8090`, acrescente `APP_PORT=<porta>`. Com GPU, acrescente `COMPOSE_FILE=compose.yaml;compose.gpu.yaml` no
Windows ou `COMPOSE_FILE=compose.yaml:compose.gpu.yaml` no Linux.

Crie `docs/configuracao.md`, trocando os valores:

`````markdown
# Configuração deste computador

Decisões tomadas ao criar o projeto. Os segredos ficam só no `.env`.

| Item | Valor |
|---|---|
| Modelo de chat | <modelo> |
| Modelo de embeddings | nomic-embed-text |
| GPU NVIDIA | <nome e memória, ou "não usada"> |
| Memória para o Docker | <memória> GB |
| Endereço | http://localhost:<porta> |
`````

Crie o `LICENSE.txt`, trocando `<ano>` e `<titular-da-licenca>`:

{blocks(["LICENSE.txt"])}
## Verificação

- O `.env` tem as três variáveis, e as duas chaves são diferentes (confira sem mostrar os valores).
- `docs/configuracao.md` e `LICENSE.txt` existem, sem marcadores por trocar.

## Depois de executar

Nesta etapa não há commit: o `.gitignore` é criado na próxima.

## Orientação ao terminar

> **Pronto:** escolhido o modelo `<modelo>`. Daqui em diante é automático. **Você não precisa fazer nada**, só deixar o
> Docker aberto e o computador ligado, com internet. O próximo passo baixa imagens e o modelo.
"""

F01 = f"""# Estrutura inicial e serviços de IA no Docker

**Etapa:** 1 de 5
**Requer:** etapa 0 (`.env` e `docs/configuracao.md`)

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar a estrutura do projeto e baixar o Ollama, o ChromaDB, o PostgreSQL, o
> SearXNG e o modelo de IA. **É a parte mais demorada:** de alguns minutos a mais de uma hora, conforme a internet e o
> modelo.
> **O que você precisa fazer:** nada. Deixe o Docker aberto. Para acompanhar o download, em outro terminal:
> `docker compose logs -f ollama-init`. Se a barra parecer parada, é normal por alguns minutos.

## Prompt

Você está criando o **Celke IA Local**. Nesta etapa, crie os arquivos da raiz: o Compose com todos os serviços, a
configuração do SearXNG e os scripts de inicialização. Backend e frontend chegam nas próximas etapas: crie as pastas
vazias `backend` e `frontend`.

Decisões já tomadas: só o `frontend` publica porta, em `127.0.0.1`; o Ollama roda no Docker (imagem fixa `0.40.13`); o
serviço `ollama-init` baixa só os modelos ausentes; o modelo vem de `CHAT_MODEL` no `.env`; a busca na internet usa o
SearXNG local e só é acionada pelo usuário.

{RULES}
Depois, deixe `scripts/iniciar.sh` executável: `chmod +x scripts/iniciar.sh`.

{blocks(ROOT)}
## Verificação

```bash
docker compose config -q && echo compose-ok
docker compose up -d ollama chroma postgres searxng ollama-init
docker wait celke-ia-local-ollama-init-1       # 0 ao terminar o download; pode levar muito tempo
docker compose ps                              # ollama, chroma, postgres e searxng healthy, sem porta publicada
docker compose exec -T ollama ollama list      # o modelo do .env e nomic-embed-text:latest
docker compose exec -T postgres psql -U celke celke_ia_local -c "select version()"
```

Rode o download em segundo plano, se a sua ferramenta permitir, e avise o usuário a cada etapa concluída. Se o
`ollama-init` terminar com erro, veja `docker compose logs ollama-init`: repita `docker compose up ollama-init` se foi
queda de internet.

Com GPU, confira que o Ollama a detectou: `docker compose logs ollama` tem `inference compute` com o nome da placa.

## Depois de executar

```bash
git add .gitignore .gitattributes .dockerignore .env.example compose.yaml compose.gpu.yaml compose.dev.yaml searxng scripts LICENSE.txt docs/configuracao.md
git update-index --chmod=+x scripts/iniciar.sh
git commit -m "chore: cria a estrutura inicial e os serviços de IA no Docker"
```

## Orientação ao terminar

> **Pronto:** os serviços de IA estão no ar e o modelo foi baixado. Ele não será baixado de novo. Continue sem fazer nada.
"""

F02 = f"""# Backend Python e RAG

**Etapa:** 2 de 5
**Requer:** etapa 1

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar a API em Python que lê os PDFs, busca os trechos e conversa com o modelo.
> Leva alguns minutos, e os testes rodam no Docker. **O que você precisa fazer:** nada.

## Prompt

Crie o backend do **Celke IA Local** em FastAPI: envio e processamento de PDFs com PyMuPDF, trechos com sobreposição,
embeddings no Ollama, vetores no ChromaDB, conversas no PostgreSQL, chat com streaming (Server-Sent Events) e busca na
internet sob demanda, que recusa endereços internos.

{RULES}
{blocks(BACKEND)}
## Verificação

```bash
docker compose --profile test run --rm --build backend-tests
docker compose --profile test rm -fs postgres-test
```

Precisa terminar com Ruff sem erros e todos os testes passando (1 desmarcado: o de integração, da etapa 4). Os testes
não usam o Ollama nem baixam modelos.

## Depois de executar

```bash
git add backend
git commit -m "feat: cria o backend com RAG sobre PDFs, conversas e busca na internet"
```

## Orientação ao terminar

> **Pronto:** o backend está criado e os testes passaram. Continue sem fazer nada.
"""

F03 = f"""# Frontend React com o Kole

**Etapa:** 3 de 5
**Requer:** etapa 2

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar as telas de Chat, Documentos e Status com o layout `@celke/kole-react`.
> **O que você precisa fazer:** nada. Ao final, a aplicação já abre no navegador.

## Prompt

Crie o frontend do **Celke IA Local** em React, TypeScript e Vite, com o `@celke/kole-react` e nginx com proxy da API.

{RULES}
{blocks(FRONTEND)}
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
curl -s -o /dev/null -w "%{{http_code}}\\n" http://localhost:<porta>/documentos   # 200
```

Use a porta de `docs/configuracao.md`. No Windows PowerShell, escreva `curl.exe`.

## Depois de executar

```bash
git add frontend
git commit -m "feat: cria o frontend com chat, documentos e status"
```

## Orientação ao terminar

> **Pronto:** a aplicação já abre em http://localhost:<porta>, mas ainda vou testar tudo. Continue sem fazer nada.
"""

F04 = """# Integração ponta a ponta

**Etapa:** 4 de 5
**Requer:** etapa 3

## Orientação antes de começar

> **O que vai acontecer agora:** vou testar o fluxo completo com o modelo real: enviar um PDF, perguntar, conferir as
> fontes, reiniciar e ver se os dados continuam. **O que você precisa fazer:** nada.

## Prompt

Teste o **Celke IA Local** como um usuário faria. Não há arquivos novos. Use os scripts criados na etapa 1, e no Windows
o `iniciar.ps1`. Se algo falhar, corrija a causa, repita a verificação e relate o que mudou.

Não apague nada além do que você mesmo criar neste teste, sempre pelo id.

## Verificação

1. Duas vezes, para confirmar que a segunda não baixa nada: `./scripts/iniciar.sh` ou
   `powershell -ExecutionPolicy Bypass -File scripts\\iniciar.ps1`. Termina com "Pronto! Abra http://localhost:<porta>".
2. `docker compose --profile test run --rm --build backend-tests pytest -m integration -v` (1 passou) e
   `docker compose --profile test rm -fs postgres-test`.
3. Crie um PDF de teste dentro do container e copie para a pasta de trabalho temporária, fora do repositório:

   ```bash
   docker compose exec -T backend python -c "import pymupdf; d=pymupdf.open(); p=d.new_page(); p.insert_text((72,72),'Manual da Padaria Aurora. O forno deve ser limpo toda quinta-feira as 15 horas.'); d.save('/tmp/manual.pdf')"
   docker cp "$(docker compose ps -q backend):/tmp/manual.pdf" <pasta temporária>/manual.pdf
   ```

4. Envie o PDF e espere a situação `pronto`. Pergunte "Quando o forno deve ser limpo?" e confira: eventos `conversation`,
   `sources`, `token` (chegando aos poucos) e `done`; fonte com `manual.pdf`, página 1; resposta correta, sem raciocínio nem
   `</think>`. Use `curl.exe`, `-N` e o JSON em arquivo no Windows:

   ```bash
   curl -F "file=@<pasta temporária>/manual.pdf;type=application/pdf" http://localhost:<porta>/api/documents
   curl -N -X POST http://localhost:<porta>/api/chat -H "Content-Type: application/json" -d "@pergunta.json"
   ```

5. Pergunte algo fora do PDF ("Qual é a capital da Austrália?"): deve vir o evento `not_found`. Repita com
   `"web_search": true`: fontes com `"kind": "web"`. Se não houver internet ou o buscador limitar os pedidos, registre como
   pendência, sem tratar como erro do projeto.
6. Persistência: `docker compose down` (**sem** `-v`), rode o script de novo e confira que `/api/documents/stats` mostra o
   documento e `/api/conversations` mostra as conversas.
7. Exclua, pelo id, as conversas e o documento deste teste. Depois disso, `/api/documents/stats` deve mostrar `total: 0`.

## Depois de executar

Só há commit se algo foi corrigido, com a mensagem `fix: <o que foi corrigido>`.

## Orientação ao terminar

> **Pronto:** o fluxo completo foi testado com o modelo real. Falta só a documentação. Continue sem fazer nada.
"""

F05 = f"""# Documentação e entrega

**Etapa:** 5 de 5
**Requer:** etapa 4

## Orientação antes de começar

> **O que vai acontecer agora:** vou criar o README e o guia para agentes de IA e fazer a entrega final.
> **O que você precisa fazer:** nada por enquanto. No final, mostro como testar no navegador.

## Prompt

Crie a documentação do **Celke IA Local**, deixe os prompts no projeto e crie a branch de homologação. Os arquivos de
`docs/prompts` são os mesmos passos em texto, para o tutorial, e `docs/gerador-prompts` mantém estes prompts atualizados:
crie-os como estão, sem executá-los.

{RULES}
Troque `<url-do-repositório>` no `README.md` pela URL do `origin`, se houver. Sem `origin`, mantenha o marcador.

{blocks(DOCS)}
Por fim, se a pasta de prompts não for `docs/prompts-iniciais/`, copie-a para lá, sem o `progresso.md`. Se esse caminho
estiver em `.git/info/exclude`, troque a linha por `/docs/prompts-iniciais/progresso.md`.

## Verificação

```bash
docker compose config -q && echo ok
docker compose ps
git status --short    # .env não aparece
```

Confira que os links internos do README existem (`.env.example`, `LICENSE.txt`, `docs/prompts-iniciais/README.md`).

## Depois de executar

```bash
git add README.md CLAUDE.md docs
git commit -m "docs: adiciona o README, o guia para agentes e os prompts"
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
"""

README = """# Prompts iniciais

Prompts para criar o **Celke IA Local** do zero com um agente de IA com acesso ao terminal (Claude Code ou similar):
chatbot com RAG sobre PDFs, modelo de IA rodando no seu computador, backend Python, frontend React com o layout
`@celke/kole-react` e Docker.

**Esta pasta basta sozinha.** Você não precisa de nenhum outro arquivo do projeto: os prompts trazem o código, o README, a
licença, o guia para agentes, os scripts e a configuração do Docker. O `package-lock.json` e os segredos do `.env` são gerados
durante a execução.

## O que você precisa antes

| O quê | Observação |
|---|---|
| Claude Code (ou agente similar) | Com acesso ao terminal |
| Docker Desktop (Windows, macOS) ou Docker Engine (Linux) | Se faltar, o prompt mostra como instalar |
| Git | Se faltar, o prompt mostra como instalar |
| Internet | Na criação, para baixar imagens e o modelo |
| Disco | Cerca de 8 GB mais o modelo |

**Não instale o Ollama, o Python nem o Node.** Tudo roda no Docker.

## Como usar

1. Crie uma pasta vazia para o projeto, em qualquer lugar, e copie só esta pasta `prompts-iniciais` para dentro dela.
2. Abra o Docker e espere ele iniciar.
3. Abra o Claude Code na pasta do projeto e execute:

   ```text
   Execute o prompt prompts-iniciais/prompt-para-replicar-projeto.md
   ```

4. Selecione o modelo de IA na pergunta e, se o Git não estiver configurado, preencha nome e e-mail. O prompt confere a memória, a GPU e o disco do seu computador e recomenda um
   modelo, com outras opções, inferior e superior.
5. Espere. O agente avisa o que está fazendo e o que você precisa fazer. No fim, ele mostra como testar no navegador.

Se parar no meio, execute o mesmo comando numa sessão nova: o andamento fica em `prompts-iniciais/progresso.md`.

Para gravar o tutorial etapa por etapa, execute os prompts da tabela um a um, cada um numa sessão nova, seguindo a
**Verificação** e o **Depois de executar** de cada um. Cada etapa precisa da anterior concluída.

| Ordem | Prompt | Resultado |
|---|---|---|
| 0 | [Preparação e escolha do modelo](f00-01-preparacao-e-modelo.md) | Computador conferido, modelo escolhido, `.env` e licença |
| 1 | [Estrutura inicial e Docker](f01-01-estrutura-e-docker.md) | Compose, scripts, Ollama, ChromaDB, PostgreSQL, SearXNG e modelo baixado |
| 2 | [Backend Python e RAG](f02-01-backend-e-rag.md) | API, PDFs, RAG, conversas, busca na internet e testes |
| 3 | [Frontend React com o Kole](f03-01-frontend-kole.md) | Chat, Documentos e Status |
| 4 | [Integração ponta a ponta](f04-01-integracao.md) | Fluxo completo com o modelo real e persistência |
| 5 | [Documentação e entrega](f05-01-documentacao.md) | README, guia para agentes, prompts em `docs/` e commit final |

## O que já está decidido

Para você ter o mínimo de perguntas, os prompts já decidem: tecnologias e versões, porta (`8090` ou a próxima livre), uso da
GPU NVIDIA quando disponível, modelo de embeddings, licença MIT com o seu nome do Git, senhas aleatórias e commits locais.
Você só responde: **qual modelo de IA usar** (selecionando uma opção) e, se o Git ainda não estiver configurado, **o seu nome
e e-mail** (preenchendo os campos).
"""

REPLICAR = """# Prompt para replicar o projeto

Cria o Celke IA Local completo numa execução só: a sessão do agente coordena, e cada etapa da tabela do
[README](README.md) é executada com contexto limpo.

## Antes de executar

Uma pasta vazia para o projeto, com `prompts-iniciais` dentro dela, e o Docker aberto. Na pasta do projeto, digite:

```text
Execute o prompt prompts-iniciais/prompt-para-replicar-projeto.md
```

## Prompt

Você vai construir o **Celke IA Local** executando, **na ordem**, as etapas da tabela do `README.md` da pasta de prompts.
Execute tudo automaticamente. Só pare nos casos de **Quando parar**. A pessoa pode não ser técnica: em toda mensagem, deixe
claro o que está acontecendo e **o que ela precisa fazer** (muitas vezes, nada).

Nomes usados abaixo:

- **raiz**: o diretório atual, onde o projeto é criado.
- **pasta de prompts**: a pasta que contém este arquivo. Use caminhos relativos à raiz.

### Ao começar

1. Leia `progresso.md` na pasta de prompts. Se existir, diga de qual etapa vai continuar e pule as concluídas.
2. Mostre ao usuário:

   > **Vou criar o Celke IA Local no seu computador.** São 6 etapas, e a mais demorada é o download do modelo de IA.
   > **O que você precisa fazer:** logo no início, selecionar o modelo e, se for preciso, preencher nome e e-mail do Git.
   > Depois, só deixar o Docker aberto.
   > Avisarei sempre que precisar de você. Se parar no meio, é só executar este prompt de novo.

### Etapas

1. **Etapa 0:** execute `f00-01-preparacao-e-modelo.md` você mesmo, nesta sessão, porque ela conversa com o usuário.
2. **Etapas 1 a 5:** para cada uma, nesta ordem:
   1. Mostre ao usuário a seção **Orientação antes de começar**, trocando os marcadores pelos valores de
      `docs/configuracao.md`.
   2. Dispare um subagente, em sequência e nunca em paralelo, com esta instrução. Sem subagentes disponíveis, execute você
      mesmo:

      > Leia `<pasta de prompts>/<arquivo>.md` e execute a seção `## Prompt` exatamente como está escrita, na raiz deste
      > repositório. Crie os arquivos com **exatamente** o conteúdo indicado. Rode a seção `## Verificação` e corrija o que
      > falhar. Não faça commit. Você não consegue falar com o usuário: não faça perguntas; a sua resposta final vai para o
      > coordenador. Responda com: arquivos criados, resultado de cada verificação, pendências e qualquer desvio do prompt.

   3. Leia o relatório e rode de novo os comandos principais da **Verificação**. Se algo falhar, mande corrigir e verifique de
      novo, em até três tentativas.
   4. Execute a seção `## Depois de executar`, sem `Co-Authored-By` nem menção a ferramenta de IA nas mensagens.
   5. Registre em `progresso.md`: etapa, arquivo, commit, `concluída` e pendências.
   6. Mostre ao usuário a seção **Orientação ao terminar**.

Se uma etapa levar muito tempo, como no download do modelo, avise o usuário de tempos em tempos, com o que está em andamento.

### Quando parar

- A etapa 0 pediu, ou falta a resposta das perguntas dela.
- Uma verificação falhou três vezes seguidas.
- O Docker parou de responder, acabou o espaço em disco ou caiu a internet.

Ao parar, diga em linguagem simples o que aconteceu, **o que a pessoa precisa fazer** e que depois basta executar este prompt de
novo. Não invente valores nem apague volumes ou dados que já existiam.

### Regras

- Não pule etapas nem "melhore" os arquivos: o conteúdo já foi testado junto.
- Nunca mostre as chaves do `.env`.
- Não faça push.
- No fim, mostre a **Orientação ao terminar** da etapa 5 e as pendências do `progresso.md`.
"""

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in {
        "README.md": README,
        "prompt-para-replicar-projeto.md": REPLICAR,
        "f00-01-preparacao-e-modelo.md": F00,
        "f01-01-estrutura-e-docker.md": F01,
        "f02-01-backend-e-rag.md": F02,
        "f03-01-frontend-kole.md": F03,
        "f04-01-integracao.md": F04,
        "f05-01-documentacao.md": F05,
    }.items():
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
        print(name, len(text.encode()))
``````

`docs/gerador-prompts/testar_prompts.py`:

``````python
"""Extrai os arquivos dos prompts numa pasta temporária e compara com o projeto (mesmas trocas do gerador)."""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gerar_prompts import FILES, REPO, content  # noqa: E402

PROMPTS = REPO / "docs" / "prompts-iniciais"
DEST = Path(tempfile.mkdtemp())
ORDER = ["f00-01-preparacao-e-modelo.md", "f01-01-estrutura-e-docker.md", "f02-01-backend-e-rag.md",
         "f03-01-frontend-kole.md", "f05-01-documentacao.md"]
ok = bad = 0
seen = set()
for name in ORDER:
    text = (PROMPTS / name).read_text(encoding="utf-8")
    for path, body in re.findall(r"^`([^`\n]+)`:\n\n`{6}[a-z]*\n(.*?)^`{6}$", text, re.M | re.S):
        seen.add(path)
        target = DEST / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8", newline="\n")
    for path in re.findall(r"^- `([^`\n]+)`$", text.split("arquivos **vazios**:")[1].split("\n\n")[1], re.M) if "arquivos **vazios**:" in text else []:
        seen.add(path)
        target = DEST / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

files = [f for f in FILES if f != "frontend/package-lock.json"]
for f in files:
    original = content(f)
    got = (DEST / f).read_text(encoding="utf-8") if (DEST / f).exists() else None
    if got == original or (got is not None and got.rstrip("\n") == original.rstrip("\n")):
        ok += 1
    else:
        bad += 1
        print("DIFERENTE", f, None if got is None else (len(got), len(original)))
print("iguais", ok, "diferentes", bad, "sobrando", sorted(seen - set(files)))
sys.exit(1 if bad or seen - set(files) else 0)
``````

`docs/prompts/01-estrutura-e-docker.md`:

``````markdown
# Etapa 1 — Estrutura inicial e Docker

## Contexto

Você está criando o **Celke IA Local**: uma aplicação web em que a pessoa envia PDFs, faz perguntas
sobre eles e recebe respostas geradas por um modelo de IA rodando localmente no Ollama, com RAG
(Retrieval-Augmented Generation). O projeto é usado num tutorial: precisa ser didático, reproduzível e
rodar inteiro no Docker, sem Python nem Node instalados no computador.

Arquitetura final (as etapas seguintes completam):

| Serviço | Imagem / build | Porta publicada |
|---|---|---|
| `frontend` | `./frontend` (nginx + React) | `${APP_BIND:-127.0.0.1}:${APP_PORT:-8090}:80` |
| `backend` | `./backend` (FastAPI) | nenhuma |
| `ollama` | `ollama/ollama:0.40.13` | nenhuma |
| `ollama-init` | `ollama/ollama:0.40.13` (baixa os modelos e termina) | nenhuma |
| `chroma` | `chromadb/chroma:1.5.9` | nenhuma |
| `postgres` | `postgres:18.6-alpine` (documentos, conversas e mensagens) | nenhuma |

Nesta etapa você cria a estrutura e os serviços de infraestrutura (Ollama, download dos modelos,
ChromaDB e PostgreSQL). Backend e frontend entram nas etapas 2 e 3.

## Tarefas

1. Crie as pastas:

   ```
   backend/app/{api,core,schemas,services,repositories}
   backend/tests/{unit,integration}
   frontend/src/{components,layouts,pages,services,hooks,types}
   frontend/public
   scripts/
   docs/
   ```

2. Crie o `compose.yaml` na raiz com `name: celke-ia-local` e, por enquanto, só os serviços:

   - **`ollama`**: imagem `ollama/ollama:0.40.13`, volume `ollama-models:/root/.ollama`, variável
     `OLLAMA_KEEP_ALIVE: ${OLLAMA_KEEP_ALIVE:-30m}`, healthcheck `["CMD", "ollama", "list"]`
     (intervalo 10s, `start_period` 20s, 10 tentativas), `restart: unless-stopped`, **sem** `ports`.
   - **`ollama-init`**: mesma imagem, `OLLAMA_HOST: http://ollama:11434`,
     `CHAT_MODEL: ${CHAT_MODEL:-qwen3:4b}`, `EMBEDDING_MODEL: ${EMBEDDING_MODEL:-nomic-embed-text}`,
     `entrypoint: ["/bin/sh", "-c"]` e um `command` que, para o modelo de embeddings e depois o de chat,
     executa `ollama show "$$model"`; se o modelo existir, escreve "Modelo X já instalado."; senão,
     escreve "Baixando X (só na primeira vez)..." e executa `ollama pull` (saindo com erro se falhar).
     No fim, "Modelos prontos.". `depends_on: ollama: condition: service_healthy`, `restart: "no"`.
     Assim os modelos nunca são baixados de novo ao reiniciar.
   - **`chroma`**: imagem `chromadb/chroma:1.5.9`, `ANONYMIZED_TELEMETRY: "FALSE"`, volume
     `chroma-data:/data`, `restart: unless-stopped`, **sem** `ports`. A imagem não tem `curl`; use no
     healthcheck o bash com `/dev/tcp`:
     `bash -c 'exec 3<>/dev/tcp/127.0.0.1/8000 && printf "GET /api/v2/heartbeat HTTP/1.0\r\n\r\n" >&3 && grep -q 200 <&3'`.
   - **`postgres`**: imagem `postgres:18.6-alpine`, `POSTGRES_DB: ${POSTGRES_DB:-celke_ia_local}`,
     `POSTGRES_USER: ${POSTGRES_USER:-celke}`, `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-}` (**sem**
     senha padrão: sem ela o PostgreSQL não sobe e diz por quê), volume
     `postgres-data:/var/lib/postgresql` (a partir da versão 18 os dados ficam em `18/docker` dentro
     dele), healthcheck `pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"` (intervalo 5s,
     `start_period` 10s, 10 tentativas), `restart: unless-stopped`, **sem** `ports`.
   - Declare os volumes `app-data`, `ollama-models`, `chroma-data` e `postgres-data`.

   Comente no topo do arquivo como subir (`docker compose up -d --build` ou os scripts da etapa 4).

3. Crie `compose.gpu.yaml` (override que reserva GPU NVIDIA para o `ollama` com
   `deploy.resources.reservations.devices`, `driver: nvidia`, `count: all`, `capabilities: [gpu]`,
   comentando que no Windows basta o driver NVIDIA com o Docker Desktop em WSL2 e que no Linux exige o
   NVIDIA Container Toolkit) e `compose.dev.yaml` (override que
   publica `127.0.0.1:8000:8000` no `backend`, para o Vite em desenvolvimento).

4. Crie o `.env.example` comentado, em português, com: `APP_PORT=8090`, `APP_BIND=127.0.0.1`
   (explicando que `0.0.0.0` abre para a rede local sem login), `COMPOSE_FILE` comentado nas duas
   formas (`compose.yaml;compose.gpu.yaml` no Windows, `compose.yaml:compose.gpu.yaml` no Linux, para
   ligar a GPU NVIDIA), `POSTGRES_PASSWORD=` vazio
   (obrigatória; os scripts da etapa 4 geram uma aleatória; vale só na criação do volume),
   `POSTGRES_DB=celke_ia_local`, `POSTGRES_USER=celke`, `CHAT_MODEL=qwen3:4b`,
   `EMBEDDING_MODEL=nomic-embed-text`, `EMBEDDING_DOCUMENT_PREFIX="search_document: "`,
   `EMBEDDING_QUERY_PREFIX="search_query: "` (prefixos do nomic; vazios para outros modelos),
   `CHAT_NUM_CTX=8192`, `CHAT_TEMPERATURE=0.2`, `CHAT_THINK=auto` (explicando que o `qwen3:4b` sempre
   raciocina e que `auto` separa o raciocínio da resposta), `OLLAMA_TIMEOUT_SECONDS=300`,
   `OLLAMA_KEEP_ALIVE=30m`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `RETRIEVAL_TOP_K=5`,
   `HISTORY_MAX_MESSAGES=6` e `MAX_UPLOAD_MB=25`.

5. Crie `.gitignore` (`.env`, `node_modules/`, `dist/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`,
   `.ruff_cache/`, `.venv/`, `*.log`, `.DS_Store`) e `.dockerignore` na raiz (`.git`, `.env`,
   `**/node_modules`, `**/dist`, `**/__pycache__`, `docs`). Crie também `.gitattributes` com
   `*.sh text eol=lf`, porque em clones no Windows o `sh` não executa scripts com CRLF.

6. Crie `LICENSE.txt` com a licença MIT, perguntando o titular se não houver `git config user.name`.

7. Se a pasta não for um repositório git, execute `git init -b main`.

8. Crie o `.env` com uma senha aleatória para o PostgreSQL (o arquivo fica fora do git):
   `printf 'POSTGRES_PASSWORD=%s\n' "$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')" > .env`.

## Verificação

```bash
docker compose config -q && echo compose-ok
docker compose -f compose.yaml -f compose.gpu.yaml config -q && echo gpu-ok
docker compose up -d ollama chroma postgres ollama-init
docker compose ps                       # ollama, chroma e postgres (healthy)
docker compose exec postgres psql -U celke celke_ia_local -c 'select version()'   # PostgreSQL 18.6
docker compose logs -f ollama-init      # até "Modelos prontos." (o primeiro download leva alguns minutos)
docker compose exec ollama ollama list  # qwen3:4b e nomic-embed-text:latest
docker compose up ollama-init           # segunda vez: "já instalado" para os dois, sem baixar nada
```

Nenhum serviço pode aparecer com porta publicada em `docker compose ps`.
``````

`docs/prompts/02-backend-e-rag.md`:

``````markdown
# Etapa 2 — Backend Python e RAG

## Contexto

O `compose.yaml` já tem `ollama`, `ollama-init`, `chroma` e `postgres`, e os modelos `qwen3:4b` e
`nomic-embed-text` estão baixados. Nesta etapa você cria o backend em `backend/`: API FastAPI que recebe
PDFs, extrai o texto, divide em trechos, gera embeddings no Ollama, grava no ChromaDB, responde
perguntas com streaming e guarda documentos, conversas e mensagens no PostgreSQL. Os testes unitários
não podem depender do Ollama.

## Dependências (`backend/requirements.txt`, versões fixas)

```
fastapi==0.162.0
uvicorn[standard]==0.54.0
pydantic==2.14.2
pydantic-settings==2.16.2
python-multipart==0.0.32
ollama==0.6.3
pymupdf==2.0
chromadb-client==1.5.9      # mesma versão da imagem chromadb/chroma do compose
langchain-text-splitters==1.1.3
httpx==0.28.1
psycopg[binary]==3.3.6
psycopg-pool==3.3.3
```

`requirements-dev.txt`: `-r requirements.txt`, `pytest==9.2.0`, `ruff==0.17.3`.

`pyproject.toml`: `requires-python = ">=3.13"`; pytest com `testpaths = ["tests"]`, marcador
`integration` e `addopts = "-m 'not integration'"`; Ruff com `line-length = 120`,
`target-version = "py313"`, `select = ["E", "F", "I", "B", "UP", "SIM"]` e `ignore = ["E501"]`.

## Organização

```
app/main.py                       create_app(settings=None, container=None); app = create_app()
app/core/config.py                Settings (pydantic-settings) e get_settings() com lru_cache
app/core/errors.py                AppError e subclasses; handlers de erro
app/core/container.py             Container (dataclass) e build_container(settings)
app/api/deps.py                   get_container(request) -> request.app.state.container
app/api/status.py                 /health, /status, /status/ollama, /models
app/api/documents.py              /documents...
app/api/chat.py                   /chat/documents e /chat
app/api/conversations.py          /conversations
app/schemas/{documents,chat,conversations,status}.py
app/services/pdf_extractor.py     PyMuPDF
app/services/chunker.py           RecursiveCharacterTextSplitter por página
app/services/ollama_service.py    OllamaService e o protocolo LanguageModel
app/services/document_service.py  envio, processamento, exclusão
app/services/conversation_service.py  listar, abrir e excluir conversas
app/services/rag_service.py       recuperação, prompt, eventos SSE e gravação das mensagens
app/repositories/database.py              pool de conexões e esquema do PostgreSQL
app/repositories/document_repository.py   tabela documents
app/repositories/conversation_repository.py  tabelas conversations e messages
app/repositories/vector_store.py          protocolo VectorStore e ChromaVectorStore
```

Rotas finas; regras nos serviços; persistência nos repositórios. Nomes em inglês, mensagens em
português.

## Configuração (`Settings`)

`ollama_url="http://ollama:11434"`, `ollama_timeout_seconds=300`, `chat_model="qwen3:4b"`,
`embedding_model="nomic-embed-text"`, `chat_num_ctx=8192`, `chat_temperature=0.2`,
`chat_think: Literal["auto","true","false"]="auto"`, `embedding_document_prefix="search_document: "`,
`embedding_query_prefix="search_query: "`, `embedding_batch_size=16`, `chroma_host="chroma"`,
`chroma_port=8000`, `postgres_host="postgres"`, `postgres_port=5432`, `postgres_db="celke_ia_local"`,
`postgres_user="celke"`, `postgres_password=""`, `data_dir=Path("/data")`, `max_upload_mb=25`,
`chunk_size=1000`, `chunk_overlap=200`, `retrieval_top_k=5`, `history_max_messages=6`,
`cors_origins=""` (vazio = sem CORS). Propriedades: `documents_dir` (`data_dir/documents`),
`database_conninfo` (montada com `psycopg.conninfo.make_conninfo`, `application_name="celke-ia-local"`),
`max_upload_bytes` e `cors_origin_list`.

## Erros

`AppError(message, code, status_code)` e subclasses: `NotFoundError` 404 `nao_encontrado`,
`ConflictError` 409 `conflito`, `InvalidFileError` 422 `arquivo_invalido`, `FileTooLargeError` 413
`arquivo_grande_demais`, `OllamaUnavailableError` 503 `ollama_indisponivel`, `ModelNotInstalledError`
503 `modelo_ausente`, `VectorStoreError` 503 `banco_vetorial_indisponivel`,
`DatabaseUnavailableError` 503 `banco_de_dados_indisponivel`, `EmbeddingMismatchError` 409
`embeddings_incompativeis`. Toda resposta de erro tem o formato
`{"erro": {"codigo": "...", "mensagem": "..."}}`, inclusive a validação do Pydantic
(`RequestValidationError` → 422 `dados_invalidos`, "Dados inválidos em <campo>: <msg>").

## Persistência

- **PostgreSQL** (`Database` em `repositories/database.py`): `psycopg_pool.ConnectionPool`
  (`min_size=1`, `max_size=10`, `row_factory=dict_row`), aberto no construtor esperando a primeira
  conexão; `connection()` é um context manager com uma transação (commit no fim, rollback no erro) que
  converte `PoolTimeout` e `psycopg.OperationalError` em `DatabaseUnavailableError` ("O banco de dados
  (PostgreSQL) não está respondendo. Verifique: docker compose logs postgres"); `create_schema()`
  (idempotente, `CREATE TABLE IF NOT EXISTS`, roda a cada inicialização), `ping()` (`SELECT 1`) e
  `close()`. Todo SQL com parâmetros `%s`; nomes de coluna dinâmicos só com `psycopg.sql.Identifier`.
- Tabela `documents`: `id` (uuid4 hex), `filename`, `size_bytes` (`BIGINT`), `sha256` (único),
  `page_count`, `chunk_count`, `status` (`pendente`, `processando`, `pronto`, `erro`),
  `error_message`, `embedding_model`, `created_at` e `updated_at` (`TIMESTAMPTZ DEFAULT now()`).
  `DocumentRepository(database)`: `create` (com `RETURNING *`), `get`, `get_by_sha256`, `list_all`
  (mais recentes primeiro), `list_by_ids` (`id = ANY(%s)`), `update(**campos)` (só colunas conhecidas;
  sempre atualiza `updated_at`), `delete` e `mark_interrupted()`, que na inicialização passa
  `pendente`/`processando` para `erro` com a mensagem "O processamento foi interrompido porque o
  serviço reiniciou. Clique em reprocessar.". Não nomeie métodos de `list` dentro da classe: o nome
  esconde o tipo `list` nas anotações.
- Tabela `conversations`: `id`, `title`, `document_ids TEXT[]` (sem chave estrangeira: a conversa
  continua legível depois que um documento é excluído), `created_at`, `updated_at`, índice em
  `updated_at DESC`. Tabela `messages`: `seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` (a
  ordem), `id` único, `conversation_id` com `REFERENCES conversations ON DELETE CASCADE`, `role`
  (`user`/`assistant`, com `CHECK`), `content`, `state` (`concluida`/`erro`, com `CHECK`),
  `error_message`, `sources JSONB` e `created_at`, índice em `(conversation_id, seq)`.
  `ConversationRepository(database)`: `create(title, document_ids)`, `get`, `list_all` (mais recente
  primeiro), `update_documents`, `delete` (devolve se apagou), `messages` (por `seq`),
  `add_message` (grava as fontes com `Jsonb` e atualiza o `updated_at` da conversa) e
  `delete_message`.
- **ChromaDB** (`ChromaVectorStore` com `chromadb.HttpClient`): coleção `chunks-<modelo>` (slug do
  nome do modelo, até 63 caracteres), criada com `embedding_function=None` (os vetores vêm do backend)
  e `metadata={"hnsw:space": "cosine", "embedding_model": <modelo>}`. Na primeira gravação, salve a
  dimensão dos vetores nos metadados (com `modify`, sem reenviar `hnsw:space`); depois, recuse vetores
  de outra dimensão ou coleção de outro modelo com `EmbeddingMismatchError`. Cada trecho tem id
  `<document_id>:<índice>`, o texto e os metadados `document_id`, `filename` e `page`. `search` filtra
  com `where` pelos documentos escolhidos (`$in` quando forem vários). `delete_document` apaga por
  `where={"document_id": id}`. Falhas viram `VectorStoreError`. Defina o protocolo `VectorStore`
  (`ping`, `add`, `search`, `delete_document`) para os testes usarem um dublê em memória.

## PDF e trechos

- `pdf_extractor.page_count(path)` valida e conta páginas; `extract_pdf(path)` devolve as páginas
  (número a partir de 1 e texto com `get_text("text", sort=True)`) e `has_text`. PDF com senha ou
  corrompido → `InvalidFileError` com mensagem clara.
- `chunker.split_pages(pages, chunk_size, chunk_overlap)` normaliza espaços, ignora páginas vazias e
  divide **cada página separadamente** com `RecursiveCharacterTextSplitter`
  (`separators=["\n\n", "\n", ". ", " ", ""]`), para cada trecho saber a página de origem. Sobreposição
  maior ou igual ao tamanho → `ValueError`.

## Ollama (`OllamaService`)

- Dois `ollama.Client`: um com o timeout configurado (embeddings e chat) e outro com 5 s (estado).
- `installed_models()` e `is_installed(model)` (o nome sem tag equivale a `:latest`).
- `embed(texts)` com `client.embed`.
- `chat_stream(messages)` devolve `ChatChunk(kind, text)` com `kind` `"content"` ou `"thinking"`. O
  `qwen3:4b` atual **sempre raciocina**: com `think=False`, o raciocínio vem misturado na resposta e
  termina em `</think>`. Por isso, com `chat_think="auto"`, consulte uma vez
  `client.show(model).capabilities` e use `think=True` quando houver `"thinking"`. Assim o Ollama devolve
  o raciocínio em `message.thinking`, separado de `message.content`. `true`/`false` forçam. Passe
  `options={"num_ctx": ..., "temperature": ...}`: o contexto padrão do Ollama corta o RAG sem avisar.
- Traduza as falhas: `ResponseError` 404 → `ModelNotInstalledError` com o comando
  `docker compose exec ollama ollama pull <modelo>`; erro com "memory" → memória insuficiente;
  `httpx.TimeoutException` → "demorou demais… na primeira pergunta o modelo é carregado na memória";
  falha de conexão → "Não foi possível conectar ao Ollama".

## Documentos (`DocumentService`)

- Processamento num `ThreadPoolExecutor(max_workers=1)`: um PDF por vez, fora da requisição.
- `upload(filename, content_type, stream)`: nome exibido só com o nome-base (sem caminho, sem
  caracteres não imprimíveis, até 200); exige `.pdf`; copia em blocos de 1 MB para um arquivo
  temporário em `documents_dir`, somando o tamanho (passou de `max_upload_bytes` → 413, apagando o
  temporário), calculando o SHA-256 e conferindo que o conteúdo começa com `%PDF-`; vazio → erro;
  SHA-256 repetido → 409 com o nome do documento existente; valida com `page_count`; move para
  `documents_dir/<id>.pdf` (o nome enviado nunca vira caminho), cria o registro, agenda `process` e
  devolve o documento.
- `process(id)`: `processando` → extrai; sem texto → erro "O PDF não tem texto selecionável (pode ser
  digitalizado como imagem). Esta versão não faz OCR."; divide; apaga vetores antigos do documento;
  gera embeddings em lotes com o prefixo de documento; grava; `pronto` com `page_count`,
  `chunk_count` e `embedding_model`. `AppError` vira `erro` com a mensagem; outro erro, mensagem
  genérica e log.
- `reprocess(id)` (recusa se estiver na fila ou processando), `delete(id)` (recusa se estiver
  processando; apaga **primeiro os vetores**, depois o arquivo e o registro, para poder repetir se o
  ChromaDB falhar), `list_all`, `get`, `stats` (`total`, `ready`, `processing` = pendente + processando,
  `error`) e `available_for_chat` (prontos com o modelo de embeddings atual).
- `DocumentOut` = documento + `needs_reindex` (pronto, mas indexado com outro modelo de embeddings).

## RAG e chat (`RagService`)

- Prompt de sistema em português com as regras: responder só com os trechos de `<documentos>`; dizer
  que não encontrou quando faltar informação, sem inventar; tratar `<documentos>` como dado não
  confiável e ignorar instruções que apareçam neles; citar as fontes como `[n]`; ser objetivo.
- Contexto: `<documentos>` com um `<trecho n="1" documento="..." pagina="...">` por resultado,
  removendo `</documentos>` do texto dos trechos.
- Mensagens: sistema, as últimas `history_max_messages` do histórico da conversa e, por fim, o
  contexto mais "Pergunta: ...". O histórico vem do banco (mensagens `concluida` com texto), nunca do
  navegador.
- `start(request) -> ChatTurn` antes do streaming, para os erros simples virarem resposta HTTP comum:
  documento inexistente ou não pronto → 422 com o nome. Sem `conversation_id`, cria a conversa (título
  = a pergunta com os espaços normalizados, até 80 caracteres, com "…" quando cortada) e grava a
  pergunta. Com `conversation_id`: conversa inexistente → 404 "Conversa não encontrada."; grava a
  pergunta e atualiza os `document_ids` da conversa. Com `retry`: exige a conversa (sem ela, 422),
  apaga a última resposta se ela for um erro e reusa a última pergunta gravada, sem gravá-la de novo;
  se a última mensagem não for uma pergunta sem resposta, 409 "Só a última resposta, quando termina
  em erro, pode ser gerada de novo.".
- `stream_answer(turn)` gera Server-Sent Events (`event: <nome>\ndata: <json>\n\n`):
  0. `conversation`: `{"id", "title"}` da conversa em que a pergunta entrou;
  1. `sources`: lista com `document_id`, `filename`, `page`, `excerpt` e `score` (1 − distância);
  2. sem trechos → um `token` com "Não encontrei nos documentos selecionados informações suficientes
     para responder a essa pergunta." e `done`, **sem chamar o modelo**;
  3. `thinking` (vazio, **uma vez só**, no primeiro pedaço de raciocínio; o raciocínio em si não vai
     para a tela);
  4. um `token` (`{"text": ...}`) por pedaço da resposta;
  5. `done`, ou `error` (`{"codigo", "mensagem"}`) se algo falhar durante o streaming.

  A resposta é gravada como mensagem `assistant` com as fontes **antes** do `done` (quem recarregar a
  página logo depois já a encontra); com `state="erro"` e `error_message` quando falhar; e, num
  `finally`, com o texto que já tinha chegado (ou "Resposta interrompida.") quando o navegador fechar a
  conexão no meio. Falha ao gravar a resposta só vai para o log.

## API (prefixo `/api`, Swagger em `/api/docs`, OpenAPI em `/api/openapi.json`)

| Método e rota | Resposta |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /status` | backend, ollama (`online`, `chat_model` e `embedding_model` com `name` e `installed`, `error`), `vector_store` e `database` |
| `GET /status/ollama` | só a parte do Ollama |
| `GET /models` | modelos instalados (`name`, `size_bytes`) |
| `GET /documents` | `{"items": [...]}` |
| `GET /documents/stats` | contagens (declare antes de `/{document_id}`) |
| `POST /documents` | multipart `file` → 202 com o documento |
| `GET /documents/{id}` | documento e situação |
| `POST /documents/{id}/reprocess` | 202 |
| `DELETE /documents/{id}` | 204 |
| `GET /chat/documents` | documentos prontos para o chat |
| `POST /chat` | `{"question" (1–4000), "document_ids" (até 50; obrigatório sem `web_search`), "conversation_id" (opcional), "retry" (padrão false), "web_search" (padrão false)}` → `text/event-stream` com `Cache-Control: no-cache` e `X-Accel-Buffering: no` |
| `GET /conversations` | `{"items": [...]}` com `id`, `title`, `document_ids`, `created_at`, `updated_at` |
| `GET /conversations/{id}` | a conversa com `messages` (`id`, `role`, `content`, `state`, `error_message`, `sources`, `created_at`) |
| `DELETE /conversations/{id}` | 204; apaga as mensagens e mantém os documentos |

Use `summary`, `tags` em português e `response_model` em todas as rotas. Na inicialização (`lifespan`),
crie o container, chame `database.create_schema()` e `mark_interrupted()`; no encerramento,
`executor.shutdown(wait=False, cancel_futures=True)` e, se o container foi criado ali (não veio dos
testes), `database.close()`. Só adicione o `CORSMiddleware` se `cors_origins` tiver valor.

## Docker (`backend/Dockerfile`)

Base `python:3.13-slim`, usuário `app` (uid 1000) dono de `/app` e `/data`. Estágios:

- `base`: instala `requirements.txt`;
- `test`: instala `requirements-dev.txt`, copia tudo com `--chown=app:app` e roda
  `ruff check . && ruff format --check . && pytest`;
- `runtime`: copia `app/`, `USER app`, healthcheck em Python (`urllib`) para `/api/health` e
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

`backend/.dockerignore`: caches do Python e `.env`.

No `compose.yaml`, acrescente o serviço `backend` (build `./backend`, target `runtime`), com todas as
variáveis do `.env.example` repassadas com padrão (`CHAT_MODEL: ${CHAT_MODEL:-qwen3:4b}`…; os prefixos
entre aspas, porque têm `: `), `OLLAMA_URL: http://ollama:11434`, `CHROMA_HOST: chroma`,
`POSTGRES_HOST: postgres`, `POSTGRES_PORT: 5432`, `POSTGRES_DB`/`POSTGRES_USER` com padrão,
`POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-}` (sem padrão), `DATA_DIR: /data`, volume `app-data:/data`
(os PDFs), `depends_on` com `postgres`, `chroma` e `ollama` saudáveis, sem `ports`. Acrescente também:

- `postgres-test` (`profiles: [test]`, `postgres:18.6-alpine`, `POSTGRES_DB: celke_ia_local_test`,
  `POSTGRES_USER: celke`, `POSTGRES_HOST_AUTH_METHOD: trust`, `tmpfs: /var/lib/postgresql`,
  healthcheck com `pg_isready`): banco descartável dos testes, sem senha e sem volume;
- `backend-tests` (`profiles: [test]`, target `test`, `DATA_DIR: /tmp/data`,
  `POSTGRES_HOST: postgres-test`, `POSTGRES_DB: celke_ia_local_test`, `POSTGRES_USER: celke`,
  `INTEGRATION_API_URL: http://backend:8000/api`, `depends_on` com `postgres-test` saudável).

## Busca na internet

A busca é opcional e só acontece quando a pessoa pede (`web_search: true` em `POST /chat`). `document_ids`
passa a ser opcional só nesse caso; sem documentos nem busca, erro 422 pedindo um documento.

- No `compose.yaml`, serviço `searxng` (imagem `searxng/searxng` com tag de data fixa, `SEARXNG_SECRET:
  ${SEARXNG_SECRET:-}`, `SEARXNG_BASE_URL: http://searxng:8080/`, `FORCE_OWNERSHIP: "false"`, volume
  `./searxng/settings.yml:/etc/searxng/settings.yml:ro`, healthcheck com `wget` em `/healthz`, **sem**
  `ports`). O backend não depende dele para subir. `searxng/settings.yml`: `use_default_settings` com
  `keep_only` de `duckduckgo`, `brave`, `mojeek` e `wikipedia`, `formats: [html, json]`, `limiter: false`,
  `image_proxy: false`, `enable_metrics: false`.
- Variáveis `SEARXNG_URL`, `WEB_SEARCH_TIMEOUT_SECONDS` (15), `WEB_SEARCH_MAX_RESULTS` (3) e
  `WEB_PAGE_MAX_CHARS` (2000). `.env.example` com `SEARXNG_SECRET=` vazio.
- `app/services/web_search.py`: `SearxngSearch` com `ping()` (`/healthz`) e `search(query)` (`/search` com
  `format=json`), que lê as páginas em paralelo com `httpx` e extrai o texto com `trafilatura`; falhou ou
  veio sem texto, usa o resumo do buscador. Segurança: só http(s) nas portas 80 e 443; todos os IPs do
  host precisam ser públicos (`is_global`); conecta no IP conferido, com `Host` e `sni_hostname` do site;
  no máximo 3 redirecionamentos, conferindo cada um; limite de tamanho e de tempo. Falha do SearXNG vira
  `WebSearchUnavailableError` (503, `busca_indisponivel`).
- `RagService`: com `web_search`, emite `searching`, depois `sources` com `kind: "web"`, `url` e o título
  em `filename`. O contexto vai em `<resultados_web>`, com um prompt de sistema próprio que o trata como
  dado não confiável, sem os PDFs e sem o histórico. Sem resultados, responde que a busca não trouxe nada
  sem chamar o modelo.
- O prompt de documentos manda responder exatamente com a frase de "não encontrei". Se o começo da resposta
  contiver "não encontr", emita `not_found` antes do `done`. Coluna `messages.answer_kind` (`documents`,
  `not_found` ou `web`), criada com `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. `/status` ganha `web_search`.
- Testes em `tests/unit/test_web_search.py`: só quando pedida, endereços internos e redirecionamentos
  bloqueados, fontes web, `not_found`, erro e nova tentativa.

## Testes unitários (sem Ollama)

`tests/fakes.py`: `FakeModel` (embeddings determinísticos por saco de palavras com hash em 64
dimensões, ignorando o prefixo; `chat_stream` devolve dois pedaços `thinking` e a resposta palavra por
palavra; erros configuráveis), `InMemoryVectorStore` (similaridade de cosseno, filtro por documento,
falha configurável), `ImmediateExecutor` (roda a tarefa na hora) e `make_pdf(path, pages)` com
PyMuPDF. `conftest.py` tem um `Database` de sessão (o `postgres-test`, com `create_schema()`), um
fixture `autouse` que faz `TRUNCATE documents, conversations, messages` antes de cada teste, e monta o
`Container` com esse banco, os dublês, um dublê das rotas de estado do Ollama e
`TestClient(create_app(settings, container))`, com `chunk_size=200`, `chunk_overlap=40`,
`retrieval_top_k=3` e `max_upload_mb=1`.

Cubra: extração por página, PDF sem texto e corrompido; tamanho, sobreposição e páginas vazias dos
trechos; envio com indexação; nome com `../` gravado como id; duplicado (409); não PDF e extensão
errada (422); grande demais (413, sem sobrar arquivo); PDF sem texto termina em erro com "OCR"; falha
de embeddings e reprocessamento; exclusão que mantém os outros documentos e os vetores deles; exclusão
com ChromaDB fora do ar (503, documento continua); lista e estatísticas; 404; documento interrompido
marcado na inicialização; `/status` (com `database`) e `/status/ollama` (offline e modelo ausente);
`/models`; streaming com `conversation` e `sources` primeiro, página certa, `thinking` uma vez,
raciocínio fora da resposta e `done`; prefixo `search_query: `; contexto em `<documentos>` e regra
contra instruções; busca só nos documentos escolhidos; sem contexto sem chamar o modelo; histórico da
conversa limitado a `history_max_messages`; erro do modelo como evento `error`; conversa criada na
primeira pergunta com pergunta, resposta e fontes gravadas; título curto; próxima pergunta na mesma
conversa; erro gravado e `retry` que o substitui sem repetir a pergunta; `retry` recusado depois de
uma resposta boa (409) e sem conversa (422); conversa inexistente (404); pergunta recusada não cria
conversa; exclusão da conversa mantém os documentos; conversa continua depois de excluir o
documento; resposta interrompida (`close()` no gerador) grava o que chegou ou "Resposta
interrompida."; documento não pronto (422); validação (422 `dados_invalidos`); `/chat/documents` só com
prontos; `needs_reindex`; tradução dos erros do Ollama (404, conexão, timeout, memória); `think`
automático pela capacidade (consultada uma vez) e forçado; nome da coleção por modelo.

## Verificação

```bash
docker compose --profile test run --rm --build backend-tests            # Ruff limpo e todos os testes passando
docker compose up -d --build backend
docker compose ps backend                                               # healthy
docker compose exec backend python -c "import urllib.request,json; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/status')))"
```

O `/api/status` precisa mostrar `ollama.online`, os dois modelos `installed: true`,
`vector_store.online` e `database.online`.
``````

`docs/prompts/03-frontend-kole.md`:

``````markdown
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
página busca `/api/conversations/<id>` e mostra as mensagens gravadas (com as fontes e os erros), sem
nenhum documento selecionado: a pessoa escolhe os da próxima pergunta; conversa inexistente → `Alerta` com botão "Nova conversa".
`CampoSelectMultiplo` com os documentos de `/api/chat/documents` (com busca e botão limpar) e, ao lado, o
botão "Selecionar todos",
pré-selecionando os `?doc=` da URL e descartando os que não estão prontos. `CabecalhoPagina` com o
título da conversa aberta (ou "Chat", em até 2 linhas e menor no celular, com os botões descendo para a linha de baixo quando faltar espaço) e os botões "Conversas" (ícone `history`, abre um `Dialogo`
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
O clique repete a pergunta com `web_search: true`. No `acoesExtras` do `CampoMensagem`, `MenuSuspenso` com ícone `plus`, `semSeta`, `direcao="cima"` e os itens
Documentos, Busca na internet e Enviar PDF; com a busca ligada, `Chip` removível ao lado (começa em Documentos e volta para ele ao trocar de conversa). Com a busca, a pergunta
vai com `web_search: true` e não exige documento selecionado. Resposta da web com o nome "Celke IA · Resposta da internet"
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
``````

`docs/prompts/04-integracao.md`:

``````markdown
# Etapa 4 — Integração ponta a ponta

## Contexto

Frontend, backend, Ollama e ChromaDB já sobem com o Docker Compose. Nesta etapa você cria os scripts
de inicialização com um comando só, o teste de integração com os modelos reais e confere o fluxo
completo: envio, indexação, pergunta, fontes, exclusão e persistência depois de reiniciar.

## Tarefas

1. **`scripts/iniciar.sh`** (Linux e macOS, `#!/usr/bin/env sh`, `set -eu`, executável), idempotente:
   - vai para a raiz do projeto; se `docker info` falhar, explica que o Docker não está rodando e sai;
   - se o `.env` não tiver `POSTGRES_PASSWORD` preenchido, gera uma senha aleatória
     (`od -An -N24 -tx1 /dev/urandom | tr -d ' \n'`), troca a linha vazia (ou cria o arquivo), aplica
     `chmod 600 .env` e avisa que a senha foi criada no `.env` (o mesmo para `SEARXNG_SECRET`) (a senha vale só na criação do volume,
     então nunca é trocada se já existir);
   - `docker compose up -d --build`;
   - avisa que os modelos são baixados só na primeira vez (cerca de 3 GB) e como acompanhar
     (`docker compose logs -f ollama-init` em outro terminal) e espera o `ollama-init` terminar com
     `docker wait celke-ia-local-ollama-init-1`. Não use `docker compose logs -f` em segundo plano:
     ele não termina e trava o script. Código diferente de 0 → mensagem com o comando de diagnóstico
     e saída com erro;
   - descobre a porta com `docker compose port frontend 80` e confere a API até 30 vezes (a cada 2 s)
     com `docker compose exec -T backend python -c "...urlopen('http://127.0.0.1:8000/api/health')..."`;
   - mostra o endereço da aplicação, o do Swagger (`/api/docs`) e os comandos de logs e de parar.

2. **`scripts/iniciar.ps1`** (Windows PowerShell) com o mesmo fluxo e as mesmas mensagens, sem acentos
   (o console do Windows pode não exibi-los). Use `$ErrorActionPreference = 'Continue'` e confira as
   falhas pelo `$LASTEXITCODE`: no PowerShell 5.1, com `Stop`, um aviso do Docker no stderr vira erro
   fatal em `docker info *> $null`. A senha e a chave vêm de
   `[System.Security.Cryptography.RandomNumberGenerator]`, o `.env` é lido com
   `Get-Content -Encoding UTF8` e gravado com `[System.IO.File]::WriteAllLines` (UTF-8 sem BOM, que o
   Docker Compose lê). Uso:
   `powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1`.

3. **`backend/tests/integration/test_full_flow.py`** com `pytestmark = pytest.mark.integration`, usando
   `httpx` contra `INTEGRATION_API_URL` (padrão `http://backend:8000/api`). Se `/status` mostrar algum
   modelo não instalado, `pytest.skip`. O teste cria um PDF de duas páginas com `make_pdf`, colocando
   na página 2 uma frase única (por exemplo, a senha de uma sala com um marcador baseado no horário),
   envia, espera a situação `pronto` (até 120 s), pergunta pelo streaming e confere: primeiro evento
   `conversation`, último `done`, alguma fonte da página 2 e a resposta contendo a informação da
   página 2. Depois lê `/conversations/<id>` (pergunta e resposta gravadas, com o mesmo texto do
   streaming) e exclui a conversa (204). Num `finally`, exclui o documento (204) e confere o 404 depois.

## Verificação

```bash
./scripts/iniciar.sh                    # termina com "Pronto! Abra http://localhost:8090"
./scripts/iniciar.sh                    # segunda vez: não baixa nada e termina rápido
docker compose --profile test run --rm --build backend-tests pytest -m integration -v   # 1 passed
```

Streaming pelo nginx (os `token` precisam chegar aos poucos, não todos no fim):

```bash
curl -F "file=@<um PDF com texto>;type=application/pdf" http://127.0.0.1:8090/api/documents
curl -N -X POST http://127.0.0.1:8090/api/chat -H "Content-Type: application/json" \
  -d '{"question": "<pergunta sobre o PDF>", "document_ids": ["<id>"]}'
```

A resposta não pode conter o raciocínio do modelo nem `</think>`.

Persistência:

```bash
docker compose down                     # sem -v
./scripts/iniciar.sh
curl -s http://127.0.0.1:8090/api/documents/stats    # o documento continua "pronto"
curl -s http://127.0.0.1:8090/api/conversations      # as conversas continuam
```

Pergunte de novo e confira que a resposta usa os vetores gravados antes de reiniciar. Por fim, no
navegador: envie um PDF, acompanhe a situação até **Pronto**, pergunte no chat, abra as fontes, pare uma
resposta no meio, recarregue a página (a conversa e a resposta parcial continuam), reabra a conversa
pela lista e exclua o documento.
``````

`docs/prompts/05-documentacao.md`:

``````markdown
# Etapa 5 — Documentação e guia para agentes

## Contexto

O Celke IA Local está completo e testado. Nesta etapa você escreve o `README.md`, para outra pessoa
reproduzir o projeto no próprio computador, e o `CLAUDE.md`, com as convenções para agentes de IA e
desenvolvedores. Use só comandos que você executou nas etapas anteriores e funcionalidades que existem
no código.

## Tarefas

1. **`README.md`** em português, com índice e as seções:
   - **Funcionalidades**: chat, documentos, status, RAG e proteções, como estão implementados;
   - **Arquitetura**: diagrama em texto (navegador → nginx → backend → Ollama, ChromaDB, PostgreSQL e `/data`),
     tabela dos serviços com a porta publicada (só o frontend, em `127.0.0.1:8090`), o fluxo de um PDF
     e o de uma pergunta, com os eventos do streaming e a gravação da conversa;
   - **Tecnologias** (tabela) e **Requisitos**: Docker e Compose, Git, 8 GB de RAM para o Docker,
     cerca de 6 GB de disco, internet só na primeira execução (não diga que funciona offline desde o
     início);
   - **Executar com Docker**: clonar
     (`git clone <url-do-repositório> celke-ia-local`), `.env` opcional (Linux/macOS e Windows; os
     scripts criam a senha do PostgreSQL e o arquivo precisa ser guardado),
     `./scripts/iniciar.sh` ou `scripts\iniciar.ps1`, a alternativa com
     `docker compose up -d --build` (exige `POSTGRES_PASSWORD` e `SEARXNG_SECRET` no `.env`) +
     `docker compose logs -f ollama-init`, tabela de endereços
     (aplicação, `/api/docs`, `/api/health`) e como parar;
   - **Usar a aplicação**: passo a passo no navegador (inclusive a lista de conversas) e exemplos com
     `curl` (pergunta, pergunta na mesma conversa, listar e abrir conversas), com um bloco para o
     Windows PowerShell usando `curl.exe` e o JSON em arquivo;
   - **Configuração e troca de modelos**: tabela de todas as variáveis do `.env.example`, como trocar
     o modelo de chat, o que acontece ao trocar o de embeddings (coleção nova, documentos marcados
     para reprocessar) e a GPU NVIDIA com `COMPOSE_FILE` no `.env` (no Windows, `;` como separador e
     só o driver NVIDIA; no Linux, `:` e o NVIDIA Container Toolkit);
   - **Testes**: os três comandos (`backend-tests`, `frontend-tests` e integração) e uma tabela com o
     que cada arquivo de teste cobre;
   - **Comandos úteis**: `ps`, logs de cada serviço, `psql` no container do banco, `ollama list`,
     `ollama ps`, `restart`, `docker stats`;
   - **Dados: preservar ou apagar**: os quatro volumes, `down` e `down -v`, como apagar documentos e
     conversas mantendo os modelos e a cópia de segurança com `pg_dump` (no Windows PowerShell, por
     `cmd /c`, porque o `<` não existe e o `>` do 5.1 grava em UTF-16);
   - **Atualizar o projeto**: `git pull` + script; atualizar o `@celke/kole-react` com `npm update` ou
     `npm install @celke/kole-react@latest` e commitar o `package-lock.json`;
   - **Desenvolvimento**: `compose.dev.yaml` + `npm run dev` (único caso que exige Node);
   - **Problemas comuns** (tabela sintoma → o que fazer): modelo ausente, memória insuficiente,
     primeira resposta lenta, PDF sem texto (sem OCR), processamento interrompido, PDF duplicado,
     porta ocupada, página que não abre, documentos que somem do chat depois de trocar o modelo de
     embeddings, PostgreSQL sem senha, senha diferente da usada na criação do banco, banco fora do ar
     e, no Windows, o limite de memória no `.wslconfig` e a porta reservada pelo sistema;
   - **Hardware e limitações**: velocidade em CPU e com GPU, o raciocínio do `qwen3:4b`, sem OCR,
     só a última resposta com erro pode ser gerada de novo, um PDF processado por vez;
   - **Busca na internet**, nas seções acima e em **Segurança**: só com o clique, só a pergunta sai do
     computador, buscadores usados e bloqueio de endereços internos;
   - **Segurança**: uso local, sem login, não publicar na internet como está; portas; `APP_BIND`;
     senha do PostgreSQL só no `.env`;
     arquivos com nome interno; PDF como dado não confiável; CORS desligado; usuário sem privilégios;
   - **Estrutura do projeto**, **Prompts para recriar o projeto** (link para `docs/prompts/`) e
     **Licença**.

2. **`CLAUDE.md`** com: tabela das pastas e stacks; branches (`main`, `homolog`, `feature/*`, `fix/*`)
   e commits só quando pedirem, em Conventional Commits em português, sem coautoria nem menção a
   ferramenta de IA; regras gerais (tudo no Docker, idiomas, sem segredos, só a porta do frontend,
   variável nova atualizada em `config.py`, `compose.yaml`, `.env.example` e README juntos); regras do
   backend (camadas, `AppError` e formato de erro, PostgreSQL e ChromaDB, conversas gravadas e
   histórico lido do banco, exclusão vetores primeiro, PDF
   como dado não confiável, eventos SSE espelhados no `sse.ts`, dublês nos testes unitários, comando
   de testes); regras do frontend (só componentes e props reais do Kole, props em português, estilos só
   com variáveis do tema, ícones registrados no `main.tsx`, chamadas pela `api.ts`, comando de testes);
   e a regra dos prompts em `docs/prompts/` (atualizar a etapa que cria a parte alterada, sem datas nem
   histórico).

## Verificação

```bash
grep -o '```bash' README.md | wc -l          # há blocos de comando
docker compose config -q && echo ok
```

Confira que todo comando do README existe e funciona (rode os de diagnóstico e os de teste), que todas
as variáveis do `.env.example` estão na tabela de configuração e que nenhum link interno está quebrado
(`.env.example`, `LICENSE.txt`, `docs/prompts/README.md`).
``````

`docs/prompts/README.md`:

``````markdown
# Prompts do Celke IA Local

Prompts para criar o Celke IA Local do zero com um agente de IA que tenha acesso ao terminal (Claude
Code ou similar): chatbot com RAG sobre PDFs, backend Python com FastAPI, frontend React com o layout
`@celke/kole-react`, modelos locais no Ollama, ChromaDB, PostgreSQL e Docker Compose.

## Antes de começar

- Docker com o Docker Compose em execução (`docker compose version`).
- Git.
- Internet: as etapas baixam imagens Docker, pacotes do npm e do PyPI e cerca de 3 GB de modelos.
- 8 GB de RAM livres para o Docker.
- Node.js 24 só se quiser gerar o `package-lock.json` fora do Docker (a etapa 3 explica).

## Como usar

**Opção 1: tudo numa execução.** Crie uma pasta vazia para o projeto, copie esta pasta `prompts` para
dentro dela, abra o agente na pasta do projeto e digite:

```text
Execute o prompt prompts/prompt-para-replicar-projeto.md
```

O [prompt para replicar o projeto](prompt-para-replicar-projeto.md) executa as etapas da tabela na
ordem, cada uma num subagente com contexto limpo, confere a **Verificação** de cada etapa antes da
próxima e registra o andamento em `prompts/progresso.md`. Se parar no meio, execute o mesmo comando numa
sessão nova e ele continua de onde parou.

**Opção 2: etapa por etapa** (para gravar o tutorial). Execute os prompts da tabela um a um, cada um
numa sessão nova do agente, na pasta do projeto. Siga a **Verificação** de cada prompt antes de passar
para o próximo.

| Ordem | Prompt | Resultado |
|---|---|---|
| 1 | [Estrutura inicial e Docker](01-estrutura-e-docker.md) | Pastas, `compose.yaml` com Ollama, ChromaDB, PostgreSQL e download dos modelos, `.env.example`, `.gitignore`, licença |
| 2 | [Backend Python e RAG](02-backend-e-rag.md) | API FastAPI, PDFs, trechos, embeddings, ChromaDB, chat com streaming, conversas no PostgreSQL, testes unitários |
| 3 | [Frontend React com o Kole](03-frontend-kole.md) | Chat, documentos e status, com conversas salvas, com o `@celke/kole-react`, nginx com proxy da API |
| 4 | [Integração ponta a ponta](04-integracao.md) | Scripts de inicialização, teste de integração com os modelos reais, persistência |
| 5 | [Documentação e guia para agentes](05-documentacao.md) | `README.md` completo e `CLAUDE.md` |

Cada prompt termina com a seção **Verificação**: os comandos precisam ser executados de verdade e
passar antes da próxima etapa.

## Regras que valem para todas as etapas

- Nomes de classes, funções, variáveis e arquivos em inglês; interface, mensagens e documentação em
  português do Brasil.
- Tudo roda no Docker; nenhuma etapa pode exigir Python ou Node instalados para executar ou testar.
- Não faça commit nem push, a não ser que a pessoa peça. Se pedir, mensagens em Conventional Commits em
  português, sem coautoria nem menção a ferramenta de IA.
``````

`docs/prompts/prompt-para-replicar-projeto.md`:

``````markdown
# Prompt para replicar o projeto

Cria o Celke IA Local completo numa execução só: a sessão do agente coordena e cada etapa da tabela do
[README](README.md) é executada por um subagente com contexto limpo.

## Antes de executar

- Uma pasta vazia para o projeto, com a pasta `prompts` dentro dela.
- Docker com o Docker Compose em execução.
- Internet e cerca de 6 GB livres em disco.

Abra o agente na pasta do projeto e digite:

```text
Execute o prompt prompts/prompt-para-replicar-projeto.md
```

## Prompt

Você vai construir o Celke IA Local executando, **na ordem**, as etapas da tabela do `README.md` da
pasta de prompts, sem parar entre elas. Só pare nos casos listados em **Quando parar**.

Nomes usados abaixo:

- **raiz**: o diretório atual, onde o projeto é criado.
- **pasta de prompts**: a pasta que contém este arquivo. Use caminhos relativos à raiz.

Você é o **coordenador**: não execute as etapas no seu próprio contexto.

### Preparação

1. **Progresso**: leia `progresso.md` na pasta de prompts. Se existir, retome a partir da primeira
   etapa que não está concluída.
2. **Pasta vazia**: se a raiz tiver arquivos além da pasta de prompts e não houver `progresso.md`,
   pare e avise: é um projeto existente, e as etapas gravariam por cima dele.
3. **Git**: se a raiz não for um repositório, execute `git init -b main`. Acrescente
   `/<pasta de prompts>/progresso.md` em `.git/info/exclude`.
4. **Docker**: confira `docker compose version` e `docker info`. Se o Docker não estiver rodando, pare
   e peça para a pessoa iniciá-lo.

### Para cada etapa

1. Leia o arquivo da etapa e passe o conteúdo **inteiro** a um subagente novo, com esta instrução no
   início: "Você está na raiz do projeto Celke IA Local. Execute o prompt abaixo por completo, incluindo
   a seção Verificação. Ao terminar, responda com a lista de arquivos criados ou alterados e a saída
   resumida de cada comando da Verificação."
2. Quando o subagente terminar, rode você mesmo os comandos da **Verificação** da etapa. Se algum
   falhar, mande o mesmo subagente (ou um novo, com a saída do erro) corrigir e verifique de novo. Faça
   no máximo três tentativas.
3. Registre em `progresso.md`: número da etapa, `concluída` e o resultado da verificação em uma linha.

### Quando parar

- Uma verificação falhou três vezes seguidas.
- O Docker parou de responder ou falta espaço em disco.
- Um download (imagem, pacote ou modelo) falhou por falta de internet.

Ao parar, diga qual etapa, o comando que falhou e a saída do erro.

### No fim

Mostre o endereço da aplicação (`http://localhost:8090`), o resultado das verificações de cada etapa e
os comandos para parar (`docker compose stop`) e apagar tudo (`docker compose down -v`). Não faça
commit: a pessoa decide quando commitar.
``````

Por fim, se a pasta de prompts não for `docs/prompts-iniciais/`, copie-a para lá, sem o `progresso.md`. Se esse caminho
estiver em `.git/info/exclude`, troque a linha por `/docs/prompts-iniciais/progresso.md`.

## Verificação

```bash
docker compose config -q && echo ok
docker compose ps
git status --short    # .env não aparece
```

Confira que os links internos do README existem (`.env.example`, `LICENSE.txt`, `docs/prompts-iniciais/README.md`).

## Depois de executar

```bash
git add README.md CLAUDE.md docs
git commit -m "docs: adiciona o README, o guia para agentes e os prompts"
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
