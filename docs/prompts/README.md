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
| 3 | [Frontend React com o Kole](03-frontend-kole.md) | Painel, documentos e chat com conversas salvas, com o `@celke/kole-react`, nginx com proxy da API |
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
