import { Status } from '@celke/kole-react';
import type { DocumentItem } from '../types/api';

type Severidade = 'ok' | 'info' | 'warn' | 'err' | 'neutral';

const LABELS: Record<DocumentItem['status'], { rotulo: string; severidade: Severidade }> = {
  pendente: { rotulo: 'Na fila', severidade: 'neutral' },
  processando: { rotulo: 'Processando', severidade: 'info' },
  pronto: { rotulo: 'Pronto', severidade: 'ok' },
  erro: { rotulo: 'Erro', severidade: 'err' },
};

/** Situação do documento como selo do Kole. */
export function DocumentStatusLabel({ document }: { document: DocumentItem }) {
  if (document.needs_reindex) return <Status rotulo="Reprocessar" severidade="warn" />;
  const { rotulo, severidade } = LABELS[document.status];
  return <Status rotulo={rotulo} severidade={severidade} />;
}

export function OnlineStatus({ online, rotulo }: { online: boolean; rotulo?: string }) {
  return <Status rotulo={rotulo ?? (online ? 'Conectado' : 'Desconectado')} severidade={online ? 'ok' : 'err'} />;
}
