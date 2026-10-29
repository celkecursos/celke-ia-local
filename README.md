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

- **Painel:** documentos cadastrados, prontos, processando e com erro (números reais da API); estado do
  backend, do Ollama, dos dois modelos, do ChromaDB e do PostgreSQL; atalhos para enviar PDF e conversar.
- **Documentos:** envio de um ou vários PDFs com barra de progresso; validação de extensão, conteúdo
  (`%PDF-`) e tamanho; processamento em segundo plano com a situação na tabela (na fila, processando,
  pronto, erro); nome, tamanho, páginas e data de envio; exclusão com confirmação, que remove o arquivo,
  os metadados e os vetores; reprocessamento; o mesmo PDF não entra duas vezes (SHA-256).
- **Chat:** escolha de um ou mais documentos; resposta em streaming (aparece enquanto é gerada); botão
  parar; fontes de cada resposta (documento, página e trecho); tentar novamente em caso de erro; copiar
  a resposta; conversas salvas no PostgreSQL (a conversa aberta fica no endereço `/chat?conversa=<id>`,
  então recarregar a página continua nela); lista das conversas anteriores para reabrir; exclusão de
  conversa com confirmação.
- **RAG:** extração com PyMuPDF página a página, divisão com sobreposição, embeddings no Ollama, vetores
  no ChromaDB com documento e página nos metadados, busca só nos documentos escolhidos e resposta baseada
  nos trechos. Sem trechos relevantes, o sistema diz que não encontrou a informação em vez de inventar.
- **Proteções:** o conteúdo dos PDFs é tratado como dado não confiável (instruções dentro do PDF não
  mudam as regras do assistente), arquivos gravados com nome interno, CORS desligado, Ollama, ChromaDB e
  PostgreSQL sem portas publicadas.

## Arquitetura

```
Navegador ──► frontend (nginx :8090) ──/api──► backend (FastAPI :8000) ──► ollama (:11434)
              React + Kole React                 │                            qwen3:4b, nomic-embed-text
                                                 ├──► chroma (:8000)  vetores dos trechos
                                                 ├──► postgres (:5432) documentos, conversas, mensagens
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

Os containers conversam pelos nomes dos serviços na rede do Docker.

Fluxo de um PDF: envio → validação → arquivo em `/data/documents/<id>.pdf` → extração do texto por
página → trechos de `CHUNK_SIZE` caracteres com `CHUNK_OVERLAP` de sobreposição → embeddings
(`search_document: ...`) → ChromaDB (coleção `chunks-<modelo>`) → situação **pronto**.

Fluxo de uma pergunta: embedding da pergunta (`search_query: ...`) → `RETRIEVAL_TOP_K` trechos mais
próximos dos documentos escolhidos → contexto entre `<documentos>` → modelo de chat → eventos
`conversation`, `sources`, `thinking`, `token`, `done` ou `error` (Server-Sent Events). A pergunta é
gravada na conversa antes do streaming e a resposta no fim (com as fontes, com o erro ou, se a pessoa
parar, com o que já tinha chegado). O histórico enviado ao modelo são as últimas
`HISTORY_MAX_MESSAGES` mensagens concluídas da conversa, lidas do banco.

## Tecnologias

| Parte | Tecnologias |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, [`@celke/kole-react`](https://www.npmjs.com/package/@celke/kole-react), nginx |
| Backend | Python 3.13, FastAPI, Pydantic, PyMuPDF, LangChain Text Splitters, cliente oficial do Ollama, cliente do ChromaDB, psycopg 3 |
| IA | Ollama 0.40, `qwen3:4b` (chat), `nomic-embed-text` (embeddings) |
| Banco vetorial | ChromaDB 1.5.9 |
| Banco de dados | PostgreSQL 18.6 |
| Testes | pytest, Ruff, Vitest, `tsc` |
| Infraestrutura | Docker Compose |

## Requisitos

- **Docker** com o **Docker Compose**: Docker Desktop (Windows e macOS) ou Docker Engine com o plugin
  Compose (Linux).
- **Git** para clonar (ou baixe o ZIP pelo GitHub).
- **Memória:** 8 GB de RAM livres para o Docker (o `qwen3:4b` usa cerca de 4 GB). No Docker Desktop,
  ajuste em *Settings → Resources*.
- **Disco:** cerca de 6 GB (imagens e modelos).
- **Internet na primeira execução:** para baixar as imagens e os modelos. Depois disso, a aplicação
  funciona sem internet.

## Executar com Docker

**1. Clonar o repositório**

```bash
git clone https://github.com/celkecursos/celke-ia-local-rascunho.git celke-ia-local
cd celke-ia-local
```

**2. (Opcional) Criar o `.env`** para mudar porta, modelos ou limites. Sem ele, valem os padrões, e os
scripts do passo 3 criam o arquivo com uma senha aleatória para o PostgreSQL (`POSTGRES_PASSWORD`).

```bash
cp .env.example .env          # Linux e macOS
copy .env.example .env        # Windows (cmd)
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

Sem o script, o mesmo resultado em qualquer sistema, desde que o `.env` tenha `POSTGRES_PASSWORD`
preenchido (sem senha o `postgres` não sobe):

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

1. No **Painel**, confira se todos os serviços estão verdes. Se algum modelo aparecer como ausente,
   o download ainda não terminou (`docker compose logs -f ollama-init`).
2. Em **Documentos**, escolha um ou mais PDFs e clique em **Enviar**. A tabela atualiza sozinha até a
   situação ficar **Pronto**. PDFs com erro mostram o motivo e podem ser reprocessados.
3. Em **Chat** (ou no ícone de conversa da linha do documento), escolha os documentos e pergunte.
   A primeira pergunta demora mais: o modelo é carregado na memória. Enquanto o modelo raciocina,
   aparece "Analisando os trechos dos documentos…"; depois a resposta chega aos poucos.
4. Abra **fontes** abaixo da resposta para ver de qual documento e página veio cada trecho.
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

## Configuração e troca de modelos

As variáveis ficam no `.env` (modelo completo em [`.env.example`](.env.example)). Depois de mudar,
execute `docker compose up -d` (ou o script de novo).

| Variável | Padrão | Para quê |
|---|---|---|
| `APP_PORT` | `8090` | Porta da aplicação no seu computador |
| `APP_BIND` | `127.0.0.1` | `0.0.0.0` abre para a rede local (ver [Segurança](#segurança)) |
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
| `MAX_UPLOAD_MB` | `25` | Tamanho máximo de cada PDF |
| `OLLAMA_KEEP_ALIVE` | `30m` | Tempo que o modelo fica na memória depois da última pergunta |

**Trocar o modelo de chat** (por exemplo `qwen3:8b`, que exige mais memória): mude `CHAT_MODEL` e rode
`./scripts/iniciar.sh`. O `ollama-init` baixa o novo modelo; o antigo continua no volume (apague com
`docker compose exec ollama ollama rm qwen3:4b`).

**Trocar o modelo de embeddings:** mude `EMBEDDING_MODEL` (e os prefixos). Cada modelo de embeddings tem
a própria coleção no ChromaDB, porque vetores de modelos diferentes não podem ser comparados. Os
documentos já enviados aparecem como **Reprocessar** e saem do chat até serem reprocessados.

**GPU NVIDIA** (Linux ou Windows com WSL2, com o
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)):

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up -d
```

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
| `tests/integration/test_full_flow.py` | Fluxo completo com Ollama, ChromaDB e PostgreSQL reais |
| `frontend/src/services/sse.test.ts` | Leitura do streaming (blocos partidos, `\r\n`) |

## Comandos úteis

```bash
docker compose ps                         # situação dos containers
docker compose logs -f backend            # logs da API e do processamento dos PDFs
docker compose logs -f ollama ollama-init # logs do Ollama e do download dos modelos
docker compose logs --tail 100 frontend   # logs do nginx
docker compose logs postgres              # logs do banco de dados
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

**Vindo de uma versão com SQLite:** na primeira subida com o PostgreSQL, o backend importa os documentos
do `/data/app.db` (os vetores no ChromaDB continuam valendo) e renomeia o arquivo para
`app.db.importado`, que fica como cópia de segurança.

## Atualizar o projeto

```bash
git pull
./scripts/iniciar.sh         # reconstrói as imagens e mantém os dados
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
| Modelo **ausente** no Painel | O download não terminou ou falhou: `docker compose logs ollama-init`. Para tentar de novo: `docker compose up ollama-init` |
| "Ollama não tem memória suficiente" | Aumente a memória do Docker Desktop, feche outros programas ou use um modelo menor (`CHAT_MODEL=qwen3:1.7b`) |
| A primeira resposta demora ou dá timeout | O modelo está sendo carregado; tente de novo. Em CPU, respostas longas levam dezenas de segundos. Aumente `OLLAMA_TIMEOUT_SECONDS` se precisar |
| PDF com erro "não tem texto selecionável" | O PDF é uma imagem digitalizada. Esta versão não faz OCR |
| PDF com erro "processamento interrompido" | O backend reiniciou durante o processamento. Clique em **Reprocessar** |
| "Este PDF já foi enviado" | O mesmo arquivo (mesmo conteúdo) já está na lista |
| Porta 8090 ocupada | Defina outra no `.env` (`APP_PORT=8091`) |
| Página não abre | `docker compose ps` (todos `healthy`?) e `docker compose logs backend frontend` |
| Mudou o modelo de embeddings e os documentos sumiram do chat | Reprocesse cada documento em **Documentos** |
| `postgres` não sobe: "superuser password is not specified" | Falta `POSTGRES_PASSWORD` no `.env`. Rode `./scripts/iniciar.sh` (cria a senha) ou preencha à mão |
| Backend reinicia em loop com "password authentication failed" | O `.env` tem uma senha diferente da usada na criação do banco. Volte a senha antiga ou, para começar do zero, apague o volume `celke-ia-local_postgres-data` (perde documentos e conversas) |
| "O banco de dados (PostgreSQL) não está respondendo" | `docker compose ps postgres` e `docker compose logs postgres` |

## Hardware e limitações

- Sem GPU, o `qwen3:4b` gera cerca de 10 a 20 palavras por segundo num processador recente de 8 núcleos;
  computadores mais simples são mais lentos. Com GPU NVIDIA, a resposta é várias vezes mais rápida.
- O `qwen3:4b` raciocina antes de responder; a resposta começa depois de alguns segundos.
- Não há OCR: PDFs digitalizados como imagem não são lidos.
- Só a última resposta, quando dá erro, pode ser gerada de novo; as conversas não têm busca nem renomeação.
- Um PDF é processado por vez; os demais aguardam na fila.

## Segurança

A aplicação foi feita para uso local, num computador pessoal. **Não a publique na internet como está:**
não há login, e qualquer pessoa com acesso ao endereço pode enviar, ler e apagar documentos.

- Só a porta do frontend é publicada, e apenas em `127.0.0.1`. O Ollama, o ChromaDB e o PostgreSQL não
  têm porta no host.
- A senha do PostgreSQL fica só no `.env` (fora do git), gerada aleatoriamente pelos scripts.
- `APP_BIND=0.0.0.0` abre a aplicação para a rede local; use só em rede confiável.
- Os arquivos são gravados com um identificador interno (o nome enviado nunca vira caminho), com limite
  de tamanho e verificação do conteúdo.
- O texto dos PDFs vai ao modelo como dado, e o prompt de sistema manda ignorar instruções que apareçam
  nele. O modelo não executa comandos nem acessa arquivos.
- O CORS fica desligado: o navegador acessa a API pelo nginx, na mesma origem.
- Os containers do backend rodam com usuário sem privilégios; nenhum usa modo privilegiado.

## Estrutura do projeto

```
backend/     API FastAPI: app/api (rotas), core (configuração, erros), schemas, services
             (PDF, trechos, Ollama, documentos, conversas, RAG), repositories (PostgreSQL,
             ChromaDB) e tests/
frontend/    React + Vite com o Kole React: layouts, pages, services (API e streaming), hooks; nginx
scripts/     iniciar.sh (Linux e macOS) e iniciar.ps1 (Windows)
docs/        Prompts para recriar o projeto do zero
compose.yaml           Serviços, volumes e perfis de teste
compose.gpu.yaml       GPU NVIDIA para o Ollama
compose.dev.yaml       API publicada para o Vite em desenvolvimento
```

## Prompts para recriar o projeto

[`docs/prompts/`](docs/prompts/README.md) tem os prompts que criam este projeto do zero com um agente
de IA (Claude Code ou outro com acesso ao terminal), etapa por etapa ou numa execução só.

## Licença

MIT. Veja [LICENSE.txt](LICENSE.txt).
