import { Estrutura } from '@celke/kole-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';

const NAV = [
  {
    itens: [
      { rotulo: 'Painel', icone: 'house', rota: '/' },
      { rotulo: 'Documentos', icone: 'file-text', rota: '/documentos' },
      { rotulo: 'Chat', icone: 'message-square', rota: '/chat' },
    ],
  },
];

export function AppLayout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <Estrutura
      marca={{ nome: 'Celke IA Local', subtitulo: 'Chat com seus PDFs', logo: '/logo.svg', href: '/' }}
      nav={NAV}
      rotaAtual={pathname}
      aoNavegar={(rota) => navigate(rota)}
      renderLink={(p) => (
        <Link to={p.href} className={p.className} onClick={p.onClick} aria-current={p['aria-current']}>
          {p.children}
        </Link>
      )}
      busca={false}
      versao="1.0.0"
      rodape={<span>Celke IA Local · os modelos rodam no seu computador com o Ollama</span>}
    >
      <Outlet />
    </Estrutura>
  );
}
