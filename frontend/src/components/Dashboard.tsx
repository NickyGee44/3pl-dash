import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { AuditRunSummary } from '../types'
import './Dashboard.css'

export default function Dashboard() {
  const [audits, setAudits] = useState<AuditRunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalAudits: 0,
    totalShipments: 0,
    totalSpend: 0,
    totalSavings: 0,
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const response = await api.get('/audits/')
      setAudits(response.data)
      
      // Calculate aggregate stats
      const totalShipments = response.data.reduce((sum: number, a: AuditRunSummary) => sum + a.shipment_count, 0)
      const totalSpend = response.data.reduce((sum: number, a: AuditRunSummary) => (sum + (a.total_spend || 0)), 0)
      const totalSavings = response.data.reduce((sum: number, a: AuditRunSummary) => (sum + (a.theoretical_savings || 0)), 0)
      
      setStats({
        totalAudits: response.data.length,
        totalShipments,
        totalSpend,
        totalSavings,
      })
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value)
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner-large"></div>
        <p>Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Hero Section */}
      <div className="dashboard-hero">
        <h1>Freight Audit Dashboard</h1>
        <p className="hero-subtitle">Track savings opportunities and optimize your shipping costs</p>
        <Link to="/audits/new" className="btn-hero">
          <span className="btn-icon">+</span>
          Create New Audit
        </Link>
      </div>

      {/* Key Metrics Cards */}
      <div className="metrics-grid">
        <div className="metric-card primary">
          <div className="metric-icon">📊</div>
          <div className="metric-content">
            <div className="metric-label">Total Audits</div>
            <div className="metric-value">{stats.totalAudits}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">📦</div>
          <div className="metric-content">
            <div className="metric-label">Total Shipments</div>
            <div className="metric-value">{formatNumber(stats.totalShipments)}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">💰</div>
          <div className="metric-content">
            <div className="metric-label">Total Spend</div>
            <div className="metric-value">{formatCurrency(stats.totalSpend)}</div>
          </div>
        </div>

        <div className="metric-card highlight">
          <div className="metric-icon">💵</div>
          <div className="metric-content">
            <div className="metric-label">Potential Savings</div>
            <div className="metric-value">{formatCurrency(stats.totalSavings)}</div>
            {stats.totalSavings > 0 && (
              <div className="metric-savings-pct">
                {((stats.totalSavings / stats.totalSpend) * 100).toFixed(1)}% savings opportunity
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Audits */}
      <div className="recent-audits-section">
        <div className="section-header">
          <h2>Recent Audits</h2>
          <Link to="/" className="view-all-link">View All →</Link>
        </div>

        {audits.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No audits yet</h3>
            <p>Create your first audit to start analyzing freight costs and finding savings opportunities.</p>
            <Link to="/audits/new" className="btn-primary">
              Create Your First Audit
            </Link>
          </div>
        ) : (
          <div className="audits-grid">
            {audits.slice(0, 6).map((audit) => (
              <Link key={audit.id} to={`/audits/${audit.id}`} className="audit-card">
                <div className="audit-card-header">
                  <div className="audit-status" data-status={audit.status}>
                    {audit.status}
                  </div>
                  <div className="audit-date">
                    {new Date(audit.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </div>
                </div>
                <h3 className="audit-name">{audit.name}</h3>
                <p className="audit-customer">{audit.customer_name}</p>
                {audit.label && <p className="audit-period">{audit.label}</p>}
                
                <div className="audit-metrics">
                  <div className="audit-metric">
                    <span className="metric-label-small">Shipments</span>
                    <span className="metric-value-small">{formatNumber(audit.shipment_count)}</span>
                  </div>
                  <div className="audit-metric">
                    <span className="metric-label-small">Spend</span>
                    <span className="metric-value-small">{formatCurrency(audit.total_spend || 0)}</span>
                  </div>
                  {audit.theoretical_savings && audit.theoretical_savings > 0 && (
                    <div className="audit-metric savings">
                      <span className="metric-label-small">Savings</span>
                      <span className="metric-value-small highlight">{formatCurrency(audit.theoretical_savings)}</span>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

