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

Nesta etapa você cria a estrutura e os serviços de infraestrutura (Ollama, download dos modelos e
ChromaDB). Backend e frontend entram nas etapas 2 e 3.

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
   - Declare os volumes `app-data`, `ollama-models` e `chroma-data`.

   Comente no topo do arquivo como subir (`docker compose up -d --build` ou os scripts da etapa 4).

3. Crie `compose.gpu.yaml` (override que reserva GPU NVIDIA para o `ollama` com
   `deploy.resources.reservations.devices`, `driver: nvidia`, `count: all`, `capabilities: [gpu]`,
   comentando que exige o NVIDIA Container Toolkit no Linux ou WSL2) e `compose.dev.yaml` (override que
   publica `127.0.0.1:8000:8000` no `backend`, para o Vite em desenvolvimento).

4. Crie o `.env.example` comentado, em português, com: `APP_PORT=8090`, `APP_BIND=127.0.0.1`
   (explicando que `0.0.0.0` abre para a rede local sem login), `CHAT_MODEL=qwen3:4b`,
   `EMBEDDING_MODEL=nomic-embed-text`, `EMBEDDING_DOCUMENT_PREFIX="search_document: "`,
   `EMBEDDING_QUERY_PREFIX="search_query: "` (prefixos do nomic; vazios para outros modelos),
   `CHAT_NUM_CTX=8192`, `CHAT_TEMPERATURE=0.2`, `CHAT_THINK=auto` (explicando que o `qwen3:4b` sempre
   raciocina e que `auto` separa o raciocínio da resposta), `OLLAMA_TIMEOUT_SECONDS=300`,
   `OLLAMA_KEEP_ALIVE=30m`, `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `RETRIEVAL_TOP_K=5`,
   `HISTORY_MAX_MESSAGES=6` e `MAX_UPLOAD_MB=25`.

5. Crie `.gitignore` (`.env`, `node_modules/`, `dist/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`,
   `.ruff_cache/`, `.venv/`, `*.log`, `.DS_Store`) e `.dockerignore` na raiz (`.git`, `.env`,
   `**/node_modules`, `**/dist`, `**/__pycache__`, `docs`).

6. Crie `LICENSE.txt` com a licença MIT, perguntando o titular se não houver `git config user.name`.

7. Se a pasta não for um repositório git, execute `git init -b main`.

## Verificação

```bash
docker compose config -q && echo compose-ok
docker compose -f compose.yaml -f compose.gpu.yaml config -q && echo gpu-ok
docker compose up -d ollama chroma ollama-init
docker compose ps                       # ollama e chroma (healthy)
docker compose logs -f ollama-init      # até "Modelos prontos." (o primeiro download leva alguns minutos)
docker compose exec ollama ollama list  # qwen3:4b e nomic-embed-text:latest
docker compose up ollama-init           # segunda vez: "já instalado" para os dois, sem baixar nada
```

Nenhum serviço pode aparecer com porta publicada em `docker compose ps`.
