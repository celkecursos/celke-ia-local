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
