import { Botao, Vazio } from '@celke/kole-react';
import { useNavigate } from 'react-router';

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <Vazio titulo="Página não encontrada" descricao="O endereço não existe nesta aplicação." icone="circle-question-mark">
      <Botao rotulo="Ir para o painel" icone="house" onClick={() => navigate('/')} />
    </Vazio>
  );
}
