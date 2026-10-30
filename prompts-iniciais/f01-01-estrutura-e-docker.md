# Estrutura inicial e serviços de IA no Docker

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

Regras desta etapa:

- Crie os arquivos com **exatamente** o conteúdo indicado, sem melhorar nem reformatar. O conteúdo já foi
  testado junto; uma alteração aqui quebra outra etapa.
- Não pergunte nada ao usuário: as decisões estão neste prompt e em `docs/configuracao.md`.
- Mostre ao usuário as seções **Orientação** (antes de começar e ao terminar), com as suas palavras só onde
  houver marcador a trocar. Se o terminal não permitir mostrar agora, inclua no seu relatório final.
- Rode tudo o que está em **Verificação** e corrija o que falhar antes de terminar.
- Nunca mostre o valor de `POSTGRES_PASSWORD` nem de `SEARXNG_SECRET`.

Depois, deixe `scripts/iniciar.sh` executável: `chmod +x scripts/iniciar.sh`.

`.gitignore`:

``````text
.env
node_modules/
dist/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.venv/
*.log
.DS_Store
``````

`.gitattributes`:

``````text
# Scripts de shell sempre com LF, mesmo em clones no Windows: com CRLF o sh não os executa.
*.sh text eol=lf
``````

`.dockerignore`:

``````text
.git
.env
**/node_modules
**/dist
**/__pycache__
docs
``````

`.env.example`:

``````text
# Copie para .env e ajuste. Sem .env, os valores padrão do compose.yaml são usados.

# Endereço do navegador: http://localhost:8090
APP_PORT=8090
# 127.0.0.1 = só neste computador. 0.0.0.0 abre na rede local (sem login: veja "Segurança" no README).
APP_BIND=127.0.0.1

# GPU NVIDIA: descomente a linha do seu sistema (o separador muda). Sem GPU, deixe comentado.
# COMPOSE_FILE=compose.yaml;compose.gpu.yaml
# COMPOSE_FILE=compose.yaml:compose.gpu.yaml

# PostgreSQL (documentos, conversas e mensagens). Obrigatório: os scripts/iniciar.* geram uma senha
# aleatória no .env na primeira vez. O banco não tem porta publicada; a senha vale só na criação do
# volume postgres-data (para trocar depois, use ALTER USER no banco ou apague o volume).
POSTGRES_PASSWORD=
POSTGRES_DB=celke_ia_local
POSTGRES_USER=celke

# Modelos do Ollama (baixados pelo serviço ollama-init na primeira subida)
CHAT_MODEL=qwen3:4b
EMBEDDING_MODEL=nomic-embed-text
# Prefixos do nomic-embed-text. Para outro modelo de embeddings, deixe vazios.
EMBEDDING_DOCUMENT_PREFIX="search_document: "
EMBEDDING_QUERY_PREFIX="search_query: "

# Janela de contexto do modelo de chat (tokens). Mais contexto = mais memória.
CHAT_NUM_CTX=8192
CHAT_TEMPERATURE=0.2
# Raciocínio do modelo (o qwen3:4b sempre raciocina). auto = separa o raciocínio da resposta
# quando o modelo tem essa capacidade; false pede para não raciocinar (nem todo modelo obedece).
CHAT_THINK=auto
OLLAMA_TIMEOUT_SECONDS=300
# Tempo que o modelo fica carregado na memória depois da última pergunta
OLLAMA_KEEP_ALIVE=30m

# RAG
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_TOP_K=5
HISTORY_MAX_MESSAGES=6

# Busca na internet (botão "Pesquisar na internet"): só acontece com o clique, e só a pergunta sai do
# computador. SEARXNG_SECRET é obrigatória e os scripts/iniciar.* geram uma aleatória no .env.
SEARXNG_SECRET=
WEB_SEARCH_TIMEOUT_SECONDS=15
WEB_SEARCH_MAX_RESULTS=3
WEB_PAGE_MAX_CHARS=2000

# Tamanho máximo de cada PDF (MB)
MAX_UPLOAD_MB=25
``````

`compose.yaml`:

``````yaml
# Celke IA Local: frontend (nginx + React), backend (FastAPI), Ollama, ChromaDB e PostgreSQL.
# Subir: scripts/iniciar.sh / scripts/iniciar.ps1 (criam o .env com a senha do banco na primeira vez)
# ou docker compose up -d --build com POSTGRES_PASSWORD no .env (sem senha o postgres não sobe).
# Valores padrão abaixo; para mudar, copie .env.example para .env.
name: celke-ia-local

services:
  frontend:
    build:
      context: ./frontend
      target: runtime
      args:
        VITE_MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-25}
    environment:
      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-25}
    # Só no próprio computador. Para abrir na rede local, troque 127.0.0.1 por 0.0.0.0 (ver README).
    ports:
      - "${APP_BIND:-127.0.0.1}:${APP_PORT:-8090}:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      target: runtime
    environment:
      OLLAMA_URL: http://ollama:11434
      OLLAMA_TIMEOUT_SECONDS: ${OLLAMA_TIMEOUT_SECONDS:-300}
      CHAT_MODEL: ${CHAT_MODEL:-qwen3:4b}
      EMBEDDING_MODEL: ${EMBEDDING_MODEL:-nomic-embed-text}
      CHAT_NUM_CTX: ${CHAT_NUM_CTX:-8192}
      CHAT_TEMPERATURE: ${CHAT_TEMPERATURE:-0.2}
      CHAT_THINK: ${CHAT_THINK:-auto}
      EMBEDDING_DOCUMENT_PREFIX: "${EMBEDDING_DOCUMENT_PREFIX-search_document: }"
      EMBEDDING_QUERY_PREFIX: "${EMBEDDING_QUERY_PREFIX-search_query: }"
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-celke_ia_local}
      POSTGRES_USER: ${POSTGRES_USER:-celke}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-}
      DATA_DIR: /data
      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-25}
      CHUNK_SIZE: ${CHUNK_SIZE:-1000}
      CHUNK_OVERLAP: ${CHUNK_OVERLAP:-200}
      RETRIEVAL_TOP_K: ${RETRIEVAL_TOP_K:-5}
      HISTORY_MAX_MESSAGES: ${HISTORY_MAX_MESSAGES:-6}
      SEARXNG_URL: http://searxng:8080
      WEB_SEARCH_TIMEOUT_SECONDS: ${WEB_SEARCH_TIMEOUT_SECONDS:-15}
      WEB_SEARCH_MAX_RESULTS: ${WEB_SEARCH_MAX_RESULTS:-3}
      WEB_PAGE_MAX_CHARS: ${WEB_PAGE_MAX_CHARS:-2000}
    volumes:
      - app-data:/data
    depends_on:
      postgres:
        condition: service_healthy
      chroma:
        condition: service_healthy
      ollama:
        condition: service_healthy
    restart: unless-stopped

  ollama:
    image: ollama/ollama:0.40.13
    volumes:
      - ollama-models:/root/.ollama
    environment:
      OLLAMA_KEEP_ALIVE: ${OLLAMA_KEEP_ALIVE:-30m}
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      start_period: 20s
      retries: 10
    restart: unless-stopped

  # Baixa só os modelos que faltam e termina. Os modelos ficam no volume ollama-models.
  ollama-init:
    image: ollama/ollama:0.40.13
    environment:
      OLLAMA_HOST: http://ollama:11434
      CHAT_MODEL: ${CHAT_MODEL:-qwen3:4b}
      EMBEDDING_MODEL: ${EMBEDDING_MODEL:-nomic-embed-text}
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        for model in "$$EMBEDDING_MODEL" "$$CHAT_MODEL"; do
          if ollama show "$$model" > /dev/null 2>&1; then
            echo "Modelo $$model já instalado."
          else
            echo "Baixando $$model (só na primeira vez)..."
            ollama pull "$$model" || exit 1
          fi
        done
        echo "Modelos prontos."
    depends_on:
      ollama:
        condition: service_healthy
    restart: "no"

  chroma:
    image: chromadb/chroma:1.5.9
    environment:
      ANONYMIZED_TELEMETRY: "FALSE"
    volumes:
      - chroma-data:/data
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/127.0.0.1/8000 && printf \"GET /api/v2/heartbeat HTTP/1.0\\r\\n\\r\\n\" >&3 && grep -q 200 <&3'"]
      interval: 10s
      timeout: 5s
      start_period: 10s
      retries: 10
    restart: unless-stopped

  # Busca da opção "Pesquisar na internet": só pesquisa quando a pessoa clica. O backend não depende dele
  # para subir: sem o SearXNG, o chat com os documentos continua funcionando.
  searxng:
    image: searxng/searxng:2026.10.30-1cd13d98d
    environment:
      SEARXNG_SECRET: ${SEARXNG_SECRET:-}
      SEARXNG_BASE_URL: http://searxng:8080/
      FORCE_OWNERSHIP: "false"
    volumes:
      - ./searxng/settings.yml:/etc/searxng/settings.yml:ro
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
      interval: 10s
      timeout: 5s
      start_period: 20s
      retries: 10
    restart: unless-stopped

  # Documentos, conversas e mensagens. O banco é criado na primeira subida, com a senha do .env.
  postgres:
    image: postgres:18.6-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-celke_ia_local}
      POSTGRES_USER: ${POSTGRES_USER:-celke}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-}
    volumes:
      # a partir do PostgreSQL 18 o volume fica em /var/lib/postgresql (os dados vão em 18/docker)
      - postgres-data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\""]
      interval: 5s
      timeout: 5s
      start_period: 10s
      retries: 10
    restart: unless-stopped

  # docker compose --profile test run --rm backend-tests
  backend-tests:
    profiles: [test]
    build:
      context: ./backend
      target: test
    environment:
      DATA_DIR: /tmp/data
      POSTGRES_HOST: postgres-test
      POSTGRES_DB: celke_ia_local_test
      POSTGRES_USER: celke
      INTEGRATION_API_URL: http://backend:8000/api
    depends_on:
      postgres-test:
        condition: service_healthy

  # Banco descartável dos testes unitários: em memória, sem senha e sem volume.
  postgres-test:
    profiles: [test]
    image: postgres:18.6-alpine
    environment:
      POSTGRES_DB: celke_ia_local_test
      POSTGRES_USER: celke
      POSTGRES_HOST_AUTH_METHOD: trust
    tmpfs:
      - /var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U celke -d celke_ia_local_test"]
      interval: 2s
      timeout: 5s
      retries: 15

  # docker compose --profile test run --rm frontend-tests
  frontend-tests:
    profiles: [test]
    build:
      context: ./frontend
      target: test

volumes:
  app-data:
  ollama-models:
  chroma-data:
  postgres-data:
``````

`compose.gpu.yaml`:

``````yaml
# GPU NVIDIA. Windows: basta o driver NVIDIA e o Docker Desktop com WSL2. Linux: requer o NVIDIA
# Container Toolkit. Para valer sempre, use COMPOSE_FILE no .env (ver .env.example).
# docker compose -f compose.yaml -f compose.gpu.yaml up -d
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
``````

`compose.dev.yaml`:

``````yaml
# Desenvolvimento do frontend com o Vite (npm run dev): publica a API em 127.0.0.1:8000.
# docker compose -f compose.yaml -f compose.dev.yaml up -d
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"
``````

`searxng/settings.yml`:

``````yaml
# Busca da opção "Pesquisar na internet". O container não tem porta publicada e só o backend o acessa.
# A chave secreta vem de SEARXNG_SECRET (no .env, gerada pelos scripts/iniciar.*).
use_default_settings:
  engines:
    keep_only:
      - duckduckgo
      - brave
      - mojeek
      - wikipedia

general:
  instance_name: "Celke IA Local"
  enable_metrics: false

search:
  safe_search: 1
  autocomplete: ""
  default_lang: "pt-BR"
  formats:
    - html
    - json

server:
  limiter: false
  image_proxy: false
  public_instance: false
  method: "GET"
``````

`scripts/iniciar.sh`:

``````sh
#!/usr/bin/env sh
# Sobe o Celke IA Local, espera os modelos e mostra o endereço. Pode rodar quantas vezes quiser.
set -eu
cd "$(dirname "$0")/.."

if ! docker info > /dev/null 2>&1; then
  echo "O Docker não está rodando. Abra o Docker Desktop (ou inicie o serviço docker) e tente de novo."
  exit 1
fi

# Senha do PostgreSQL e chave do SearXNG: geradas uma vez e guardadas no .env (o banco guarda a senha
# da primeira subida).
for name in POSTGRES_PASSWORD SEARXNG_SECRET; do
  if ! grep -qs "^$name=..*" .env; then
    value=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
    if [ -f .env ]; then
      grep -v "^$name=" .env > .env.tmp || true
      mv .env.tmp .env
    fi
    printf '%s=%s\n' "$name" "$value" >> .env
    chmod 600 .env
    echo "$name criada no arquivo .env (guarde o arquivo; não o envie ao git)."
  fi
done

echo "Subindo os serviços (a primeira vez constrói as imagens e pode levar alguns minutos)..."
docker compose up -d --build

echo "Aguardando os modelos (o download só acontece na primeira vez; são cerca de 3 GB)."
echo "Para ver o progresso, em outro terminal: docker compose logs -f ollama-init"
status=$(docker wait celke-ia-local-ollama-init-1)
if [ "$status" != "0" ]; then
  echo "Falha ao baixar os modelos. Veja: docker compose logs ollama-init"
  exit 1
fi

echo "Verificando a API..."
port=$(docker compose port frontend 80 | sed 's/.*://')
for _ in $(seq 1 30); do
  if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" > /dev/null 2>&1; then
    echo ""
    echo "Pronto! Abra http://localhost:$port"
    echo "Documentação da API: http://localhost:$port/api/docs"
    echo "Logs: docker compose logs -f backend    Parar: docker compose stop"
    exit 0
  fi
  sleep 2
done
echo "A API não respondeu. Veja: docker compose ps && docker compose logs backend"
exit 1
``````

`scripts/iniciar.ps1`:

``````powershell
# Sobe o Celke IA Local no Windows (PowerShell), espera os modelos e mostra o endereço.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
# Sem 'Stop': no PowerShell 5.1, um simples aviso do Docker no stderr viraria erro fatal com *> $null.
# As falhas do Docker sao conferidas pelo $LASTEXITCODE.
$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot '..')

docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host 'O Docker nao esta rodando. Abra o Docker Desktop e tente de novo.'
  exit 1
}

# Senha do PostgreSQL e chave do SearXNG: geradas uma vez e guardadas no .env (o banco guarda a senha
# da primeira subida).
$envFile = Join-Path (Get-Location) '.env'
$lines = @()
if (Test-Path $envFile) { $lines = @(Get-Content $envFile -Encoding UTF8) }
foreach ($name in 'POSTGRES_PASSWORD', 'SEARXNG_SECRET') {
  if (-not ($lines | Where-Object { $_ -match "^$name=.+" })) {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $value = -join ($bytes | ForEach-Object { $_.ToString('x2') })
    $lines = @($lines | Where-Object { $_ -notmatch "^$name=" }) + "$name=$value"
    # UTF-8 sem BOM: o Docker Compose le o .env assim
    [System.IO.File]::WriteAllLines($envFile, [string[]]$lines)
    Write-Host "$name criada no arquivo .env (guarde o arquivo; nao o envie ao git)."
  }
}

Write-Host 'Subindo os servicos (a primeira vez constroi as imagens e pode levar alguns minutos)...'
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host 'Aguardando os modelos (o download so acontece na primeira vez; sao cerca de 3 GB).'
Write-Host 'Para ver o progresso, em outro terminal: docker compose logs -f ollama-init'
$status = docker wait celke-ia-local-ollama-init-1
if ($status -ne '0') {
  Write-Host 'Falha ao baixar os modelos. Veja: docker compose logs ollama-init'
  exit 1
}

$port = ((docker compose port frontend 80) -split ':')[-1]
for ($i = 0; $i -lt 30; $i++) {
  docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host ''
    Write-Host "Pronto! Abra http://localhost:$port"
    Write-Host "Documentacao da API: http://localhost:$port/api/docs"
    Write-Host 'Logs: docker compose logs -f backend    Parar: docker compose stop'
    exit 0
  }
  Start-Sleep -Seconds 2
}
Write-Host 'A API nao respondeu. Veja: docker compose ps; docker compose logs backend'
exit 1
``````

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
