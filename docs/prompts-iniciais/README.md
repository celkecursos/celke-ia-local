# Prompts iniciais

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
