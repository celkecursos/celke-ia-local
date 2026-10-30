# Integração ponta a ponta

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
   `powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1`. Termina com "Pronto! Abra http://localhost:<porta>".
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
