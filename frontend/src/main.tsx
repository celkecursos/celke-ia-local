import '@celke/kole-react/estilos.css';
import './styles.css';
import { ProvedorUi, registrarIcones } from '@celke/kole-react';
import { Bot, Cpu, Database, Server } from 'lucide-react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { router } from './router';

// Ícones usados pelo nome que não vêm registrados no Kole
registrarIcones({ bot: Bot, cpu: Cpu, database: Database, server: Server });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProvedorUi>
      <RouterProvider router={router} />
    </ProvedorUi>
  </StrictMode>,
);
