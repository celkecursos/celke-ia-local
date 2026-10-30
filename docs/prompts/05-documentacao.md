# Etapa 5 — Documentação e guia para agentes

## Contexto

O Celke IA Local está completo e testado. Nesta etapa você escreve o `README.md`, para outra pessoa
reproduzir o projeto no próprio computador, e o `CLAUDE.md`, com as convenções para agentes de IA e
desenvolvedores. Use só comandos que você executou nas etapas anteriores e funcionalidades que existem
no código.

## Tarefas

1. **`README.md`** em português, com índice e as seções:
   - **Funcionalidades**: painel, documentos, chat, RAG e proteções, como estão implementados;
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
     `docker compose up -d --build` (exige `POSTGRES_PASSWORD` no `.env`) +
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
