# Sobe o Celke IA Local no Windows (PowerShell), espera os modelos e mostra o endereço.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host 'O Docker nao esta rodando. Abra o Docker Desktop e tente de novo.'
  exit 1
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
