import { createBrowserRouter } from 'react-router';
import { AppLayout } from './layouts/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/documentos', element: <DocumentsPage /> },
      { path: '/chat', element: <ChatPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
