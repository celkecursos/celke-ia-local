# Guia para agentes de IA e desenvolvedores

Convenções deste repositório. Leia o `README.md` antes de começar: ele descreve a arquitetura, os
comandos e as variáveis de ambiente.

| Pasta | Projeto | Stack |
|---|---|---|
| `backend/` | API, processamento dos PDFs, RAG e conversas | Python 3.13, FastAPI, Pydantic, PyMuPDF, Ollama, ChromaDB, PostgreSQL (psycopg 3) |
| `frontend/` | Painel, documentos e chat | React 19, TypeScript, Vite, React Router, `@celke/kole-react` |
| raiz | Docker Compose, scripts de inicialização | Docker Compose |
| `docs/prompts/` | Prompts que recriam o projeto do zero | Markdown |

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
- O conteúdo dos PDFs é dado não confiável: vai ao modelo dentro de `<documentos>`, nunca como
  instrução. O modelo não executa comandos nem acessa arquivos.
- O chat responde em Server-Sent Events: `conversation`, `sources`, `thinking` (uma vez), `token`,
  `done` ou `error`.
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
