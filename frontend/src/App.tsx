import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import AuditRunsList from './pages/AuditRunsList'
import NewAuditWizard from './pages/NewAuditWizard'
import AuditDetailView from './pages/AuditDetailView'
import TariffLibrary from './pages/TariffLibrary'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/audits" element={<AuditRunsList />} />
        <Route path="/audits/new" element={<NewAuditWizard />} />
        <Route path="/audits/:id" element={<AuditDetailView />} />
        <Route path="/tariffs" element={<TariffLibrary />} />
      </Routes>
    </Layout>
  )
}

export default App

