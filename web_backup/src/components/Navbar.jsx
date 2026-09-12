import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import { FEATURE_VISIBILITY } from '../config/featureVisibility';
import './Navbar.css';

export default function Navbar() {
  const navigate = useNavigate();
  const { user, setUser, setRole } = useUser();

  const handleQuickDemo = () => {
    // Set demo mode and navigate to analysis page
    setUser({ ...user, role: 'demo' });
    navigate('/analysis', {
      state: {
        quickDemo: true,
        preset: {
          topology: 'enterprise_20n',
          scenario: 'ransomware-lateral',
          episodes: 700,
          dataSource: 'hybrid',
          telemetryWeight: 0.6,
        },
      },
    });
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          Onyx
        </Link>

        <div className="navbar-links">
          <Link to="/" className="nav-link">Dashboard</Link>
          <Link to="/analysis" className="nav-link">Analysis</Link>
          <Link to="/training" className="nav-link">Training</Link>
          <Link to="/reports" className="nav-link">Reports</Link>
        </div>

        <div className="navbar-controls">
          {FEATURE_VISIBILITY.showRoleSelector && (
            <div className="user-selector">
              <label htmlFor="user-role">Role:</label>
              <select
                id="user-role"
                value={user?.role || 'executive'}
                onChange={(e) => setRole(e.target.value)}
                className="role-select"
              >
                <option value="executive">Executive</option>
                <option value="analyst">SOC Analyst</option>
                <option value="architect">Security Architect</option>
                <option value="demo">Demo/Judge</option>
              </select>
            </div>
          )}
          {FEATURE_VISIBILITY.showQuickDemoButton && (
            <button onClick={handleQuickDemo} className="btn btn-primary">
              Quick Demo
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
