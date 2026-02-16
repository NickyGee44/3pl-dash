import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  
  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }
  
  return (
    <div className="layout">
      <header className="header">
        <div className="container">
          <Link to="/" className="logo">
            <div className="logo-icon">3PL</div>
            <div className="logo-text">
              <h1>3PL Links</h1>
              <span>Freight Audit Platform</span>
            </div>
          </Link>
          <nav>
            <Link to="/" className={isActive('/') ? 'active' : ''}>Dashboard</Link>
            <Link to="/audits" className={isActive('/audits') && !isActive('/audits/new') ? 'active' : ''}>All Audits</Link>
            <Link to="/audits/new" className={isActive('/audits/new') ? 'active' : ''}>New Audit</Link>
            <Link to="/tariffs" className={isActive('/tariffs') ? 'active' : ''}>Tariff Library</Link>
          </nav>
        </div>
      </header>
      <main className="main">
        <div className="container">
          {children}
        </div>
      </main>
    </div>
  )
}

