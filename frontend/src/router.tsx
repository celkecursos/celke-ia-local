import { createBrowserRouter, Navigate, useLocation } from 'react-router';
import { AppLayout } from './layouts/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { StatusPage } from './pages/StatusPage';

// Endereço antigo do chat: mantém ?conversa= e ?doc= dos links já salvos.
function LegacyChatRedirect() {
  const { search } = useLocation();
  return <Navigate to={`/${search}`} replace />;
}

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <ChatPage /> },
      { path: '/documentos', element: <DocumentsPage /> },
      { path: '/status', element: <StatusPage /> },
      { path: '/chat', element: <LegacyChatRedirect /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
