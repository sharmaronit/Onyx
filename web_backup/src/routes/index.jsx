import { createBrowserRouter } from 'react-router-dom';
import App from '../App';
import Dashboard from '../pages/Dashboard';
import AnalysisHub from '../pages/AnalysisHub';
import Training from '../pages/Training';
import Reports from '../pages/Reports';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'analysis',
        element: <AnalysisHub />,
      },
      {
        path: 'training',
        element: <Training />,
      },
      {
        path: 'reports',
        element: <Reports />,
      },
    ],
  },
]);

export default router;
