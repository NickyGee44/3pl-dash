import { Link } from 'react-router-dom'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="layout">
      <header className="header">
        <div className="container">
          <Link to="/" className="logo">
            <h1>3PL Links</h1>
            <span>Freight Audit Platform</span>
          </Link>
          <nav>
            <Link to="/">Dashboard</Link>
            <Link to="/audits">All Audits</Link>
            <Link to="/audits/new">New Audit</Link>
            <Link to="/tariffs">Tariff Library</Link>
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

