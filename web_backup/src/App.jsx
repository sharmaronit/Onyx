import { Outlet } from 'react-router-dom';
import { UserProvider } from './contexts/UserContext';
import { SimulationProvider } from './contexts/SimulationContext';
import { ResultsProvider } from './contexts/ResultsContext';
import Navbar from './components/Navbar';
import './styles.css';

export default function App() {
  return (
    <UserProvider>
      <SimulationProvider>
        <ResultsProvider>
          <div className="app">
            <Navbar />
            <main className="main-content">
              <Outlet />
            </main>
          </div>
        </ResultsProvider>
      </SimulationProvider>
    </UserProvider>
  );
}