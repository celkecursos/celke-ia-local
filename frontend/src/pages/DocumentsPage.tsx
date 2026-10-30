import {
  AcaoLinha,
  Alerta,
  Botao,
  CabecalhoPagina,
  CampoAnexo,
  Card,
  formatBytes,
  formatDataHoraBr,
  Progresso,
  Tabela,
  useConfirmacao,
  useToast,
  type Anexo,
  type CampoAnexoRef,
  type Coluna,
} from '@celke/kole-react';
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { DocumentStatusLabel } from '../components/StatusLabel';
import { usePolling } from '../hooks/usePolling';
import { api, uploadDocument } from '../services/api';
import type { DocumentItem } from '../types/api';

// Mesmo limite do backend (MAX_UPLOAD_MB) e do nginx (client_max_body_size).
const MAX_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB ?? 25);

interface UploadState {
  name: string;
  percent: number;
}

export function DocumentsPage() {
  const toast = useToast();
  const confirmar = useConfirmacao();
  const navigate = useNavigate();
  const anexoRef = useRef<CampoAnexoRef>(null);
  const [selected, setSelected] = useState<Anexo[]>([]);
  const [upload, setUpload] = useState<UploadState | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [processing, setProcessing] = useState(false);
  const docs = usePolling(
    async () => {
      const items = await api.documents();
      setProcessing(items.some((d) => d.status === 'pendente' || d.status === 'processando'));
      return items;
    },
    2000,
    processing,
  );

  async function sendFiles() {
    const files = selected.map((a) => anexoRef.current?.arquivoDe(a)).filter((f): f is File => !!f);
    for (const file of files) {
      setUpload({ name: file.name, percent: 0 });
      try {
        await uploadDocument(file, (percent) => setUpload({ name: file.name, percent }));
        toast.ok('PDF enviado', `${file.name} está sendo processado.`);
      } catch (e) {
        toast.err(`Não foi possível enviar ${file.name}`, e instanceof Error ? e.message : undefined);
      }
    }
    setUpload(null);
    setSelected([]);
    await docs.reload();
    setProcessing(true);
  }

  async function remove(doc: DocumentItem) {
    const ok = await confirmar.remover({
      titulo: 'Excluir documento?',
      mensagem: `"${doc.filename}" e todos os trechos indexados serão removidos. Esta ação não pode ser desfeita.`,
    });
    if (!ok) return;
    setBusyId(doc.id);
    try {
      await api.deleteDocument(doc.id);
      toast.ok('Documento excluído');
      await docs.reload();
    } catch (e) {
      toast.err('Não foi possível excluir', e instanceof Error ? e.message : undefined);
    } finally {
      setBusyId(null);
    }
  }

  async function reprocess(doc: DocumentItem) {
    setBusyId(doc.id);
    try {
      await api.reprocess(doc.id);
      toast.info('Reprocessando', doc.filename);
      setProcessing(true);
      await docs.reload();
    } catch (e) {
      toast.err('Não foi possível reprocessar', e instanceof Error ? e.message : undefined);
    } finally {
      setBusyId(null);
    }
  }

  const columns: Coluna<DocumentItem>[] = [
    {
      campo: 'filename',
      rotulo: 'Arquivo',
      destaque: true,
      render: (d) => (
        <div className="app-doc-nome">
          <span>{d.filename}</span>
          {d.status === 'erro' && d.error_message && <small className="app-doc-erro">{d.error_message}</small>}
          {d.needs_reindex && <small className="app-doc-erro">Indexado com outro modelo de embeddings.</small>}
        </div>
      ),
    },
    { campo: 'size_bytes', rotulo: 'Tamanho', alinhamento: 'direita', formato: (v) => formatBytes(Number(v)) },
    { campo: 'page_count', rotulo: 'Páginas', alinhamento: 'direita', formato: (v) => (v == null ? '–' : String(v)) },
    { campo: 'created_at', rotulo: 'Enviado em', formato: (v) => formatDataHoraBr(new Date(String(v))) },
    { campo: 'status', rotulo: 'Situação', render: (d) => <DocumentStatusLabel document={d} /> },
  ];

  return (
    <div className="app-pagina">
      <CabecalhoPagina titulo="Documentos" icone="file-text" trilha>
        Envie PDFs com texto selecionável. Cada arquivo é dividido em trechos e indexado para o chat.
      </CabecalhoPagina>

      <Card titulo="Enviar PDFs">
        <CampoAnexo
          ref={anexoRef}
          rotulo="Arquivos PDF"
          dica={`Até ${MAX_MB} MB por arquivo. PDFs digitalizados como imagem não são lidos (sem OCR).`}
          accept="application/pdf,.pdf"
          maxTamanho={MAX_MB * 1024 * 1024}
          valor={selected}
          aoMudar={setSelected}
          disabled={!!upload}
        />
        {upload && (
          <div className="app-upload">
            <span>Enviando {upload.name}</span>
            <Progresso valor={upload.percent} mostrarValor="fim" rotulo={`Envio de ${upload.name}`} />
          </div>
        )}
        <div className="app-acoes">
          <Botao
            rotulo={selected.length > 1 ? `Enviar ${selected.length} arquivos` : 'Enviar'}
            icone="cloud-upload"
            disabled={!selected.length}
            carregando={!!upload}
            onClick={sendFiles}
          />
        </div>
      </Card>

      {docs.error && !docs.data && (
        <Alerta severidade="err" titulo="Não foi possível carregar os documentos" mensagem={docs.error.message} />
      )}

      <Card titulo="Documentos cadastrados" corpoSemEspaco>
        <Tabela
          colunas={columns}
          registros={docs.data ?? []}
          carregando={docs.loading}
          erro={docs.error && !!docs.data ? docs.error.message : undefined}
          aoRecarregar={docs.reload}
          vazioTitulo="Nenhum documento ainda"
          vazioDescricao="Envie um PDF acima para começar."
          vazioIcone="file-text"
          acoes={(d) => (
            <>
              {d.status === 'pronto' && !d.needs_reindex && (
                <AcaoLinha icone="message-square" rotulo="Conversar" severidade="pri" onClick={() => navigate(`/?doc=${d.id}`)} />
              )}
              {(d.status === 'erro' || d.needs_reindex) && (
                <AcaoLinha icone="refresh-cw" rotulo="Reprocessar" carregando={busyId === d.id} onClick={() => reprocess(d)} />
              )}
              <AcaoLinha
                icone="trash-2"
                rotulo="Excluir"
                severidade="err"
                disabled={d.status === 'processando'}
                carregando={busyId === d.id}
                onClick={() => remove(d)}
              />
            </>
          )}
        />
      </Card>
    </div>
  );
}
