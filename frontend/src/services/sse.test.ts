import { describe, expect, it } from 'vitest';
import { parseSseBlock, readSse } from './sse';

function streamOf(...parts: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const p of parts) controller.enqueue(encoder.encode(p));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const e of readSse(stream)) events.push(e);
  return events;
}

describe('parseSseBlock', () => {
  it('lê os seis tipos de evento', () => {
    expect(parseSseBlock('event: conversation\ndata: {"id": "c1", "title": "Pergunta"}')).toEqual({
      type: 'conversation',
      id: 'c1',
      title: 'Pergunta',
    });
    expect(parseSseBlock('event: token\ndata: {"text": "Olá"}')).toEqual({ type: 'token', text: 'Olá' });
    expect(parseSseBlock('event: done\ndata: {}')).toEqual({ type: 'done' });
    expect(parseSseBlock('event: thinking\ndata: {}')).toEqual({ type: 'thinking' });
    expect(parseSseBlock('event: error\ndata: {"codigo": "x", "mensagem": "falhou"}')).toEqual({
      type: 'error',
      code: 'x',
      message: 'falhou',
    });
    expect(parseSseBlock('event: sources\ndata: []')).toEqual({ type: 'sources', sources: [] });
  });

  it('ignora eventos desconhecidos e blocos sem dados', () => {
    expect(parseSseBlock('event: ping\ndata: {}')).toBeNull();
    expect(parseSseBlock(': comentário')).toBeNull();
  });
});

describe('readSse', () => {
  it('junta blocos partidos entre pedaços do stream', async () => {
    const events = await collect(
      streamOf('event: token\ndata: {"te', 'xt": "Ol"}\n\nevent: token\n', 'data: {"text": "á"}\n\nevent: done\ndata: {}\n\n'),
    );

    expect(events).toEqual([{ type: 'token', text: 'Ol' }, { type: 'token', text: 'á' }, { type: 'done' }]);
  });

  it('aceita quebras de linha \\r\\n e o último bloco sem linha em branco', async () => {
    const events = await collect(streamOf('event: token\r\ndata: {"text": "a"}\r\n\r\nevent: done\r\ndata: {}'));

    expect(events).toEqual([{ type: 'token', text: 'a' }, { type: 'done' }]);
  });
});
