# Etapa 4 — Integração ponta a ponta

## Contexto

Frontend, backend, Ollama e ChromaDB já sobem com o Docker Compose. Nesta etapa você cria os scripts
de inicialização com um comando só, o teste de integração com os modelos reais e confere o fluxo
completo: envio, indexação, pergunta, fontes, exclusão e persistência depois de reiniciar.

## Tarefas

1. **`scripts/iniciar.sh`** (Linux e macOS, `#!/usr/bin/env sh`, `set -eu`, executável), idempotente:
   - vai para a raiz do projeto; se `docker info` falhar, explica que o Docker não está rodando e sai;
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
   (o console do Windows pode não exibi-los). Uso:
   `powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1`.

3. **`backend/tests/integration/test_full_flow.py`** com `pytestmark = pytest.mark.integration`, usando
   `httpx` contra `INTEGRATION_API_URL` (padrão `http://backend:8000/api`). Se `/status` mostrar algum
   modelo não instalado, `pytest.skip`. O teste cria um PDF de duas páginas com `make_pdf`, colocando
   na página 2 uma frase única (por exemplo, a senha de uma sala com um marcador baseado no horário),
   envia, espera a situação `pronto` (até 120 s), pergunta pelo streaming e confere: último evento
   `done`, alguma fonte da página 2 e a resposta contendo a informação da página 2. Num `finally`,
   exclui o documento (204) e confere o 404 depois.

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
```

Pergunte de novo e confira que a resposta usa os vetores gravados antes de reiniciar. Por fim, no
navegador: envie um PDF, acompanhe a situação até **Pronto**, pergunte no chat, abra as fontes, pare uma
resposta no meio e exclua o documento.
