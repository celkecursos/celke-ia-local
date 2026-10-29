import { Alerta, Botao, CabecalhoPagina, Card, Indicador, Indicadores } from '@celke/kole-react';
import { useNavigate } from 'react-router';
import { OnlineStatus } from '../components/StatusLabel';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

export function DashboardPage() {
  const navigate = useNavigate();
  const stats = usePolling(api.stats, 5000);
  const status = usePolling(api.status, 10000);
  const s = status.data;
  const modelsMissing = s?.ollama.online && !(s.ollama.chat_model.installed && s.ollama.embedding_model.installed);

  return (
    <div className="app-pagina">
      <CabecalhoPagina
        titulo="Painel"
        icone="house"
        acoes={
          <>
            <Botao rotulo="Enviar PDF" icone="upload" onClick={() => navigate('/documentos')} />
            <Botao rotulo="Iniciar conversa" icone="message-square" severidade="secundario" onClick={() => navigate('/chat')} />
          </>
        }
      >
        Envie PDFs e faça perguntas sobre eles. As respostas são geradas por um modelo de IA rodando no seu computador.
      </CabecalhoPagina>

      {stats.error && <Alerta severidade="err" titulo="Não foi possível carregar os números" mensagem={stats.error.message} />}
      {s && !s.ollama.online && (
        <Alerta
          severidade="err"
          titulo="Ollama desconectado"
          mensagem={s.ollama.error ?? 'Verifique o container do Ollama: docker compose logs ollama'}
        />
      )}
      {modelsMissing && (
        <Alerta
          severidade="warn"
          titulo="Modelos ainda não instalados"
          mensagem="O download inicial dos modelos pode levar alguns minutos. Acompanhe com: docker compose logs -f ollama-init"
        />
      )}

      <Indicadores>
        <Indicador rotulo="Documentos cadastrados" valor={stats.data?.total ?? '–'} icone="file-text" carregando={stats.loading} />
        <Indicador
          rotulo="Prontos para o chat"
          valor={stats.data?.ready ?? '–'}
          icone="circle-check"
          cor="var(--ok-solid)"
          carregando={stats.loading}
        />
        <Indicador
          rotulo="Processando"
          valor={stats.data?.processing ?? '–'}
          icone="loader-circle"
          cor="var(--info-solid)"
          carregando={stats.loading}
        />
        <Indicador
          rotulo="Com erro"
          valor={stats.data?.error ?? '–'}
          icone="triangle-alert"
          cor="var(--err-solid)"
          carregando={stats.loading}
        />
      </Indicadores>

      <Card titulo="Serviços" subtitulo="Atualizado a cada 10 segundos">
        {status.error ? (
          <Alerta severidade="err" titulo="Backend indisponível" mensagem={status.error.message} />
        ) : (
          <ul className="app-lista-servicos">
            <li>
              <span>Backend (API)</span>
              <OnlineStatus online={!!s?.backend.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>Ollama</span>
              <OnlineStatus online={!!s?.ollama.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>
                Modelo de chat <code>{s?.ollama.chat_model.name}</code>
              </span>
              <OnlineStatus online={!!s?.ollama.chat_model.installed} rotulo={s?.ollama.chat_model.installed ? 'Instalado' : 'Ausente'} />
            </li>
            <li>
              <span>
                Modelo de embeddings <code>{s?.ollama.embedding_model.name}</code>
              </span>
              <OnlineStatus
                online={!!s?.ollama.embedding_model.installed}
                rotulo={s?.ollama.embedding_model.installed ? 'Instalado' : 'Ausente'}
              />
            </li>
            <li>
              <span>ChromaDB (banco vetorial)</span>
              <OnlineStatus online={!!s?.vector_store.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
            <li>
              <span>PostgreSQL (documentos e conversas)</span>
              <OnlineStatus online={!!s?.database.online} rotulo={s ? undefined : 'Verificando'} />
            </li>
          </ul>
        )}
      </Card>
    </div>
  );
}
