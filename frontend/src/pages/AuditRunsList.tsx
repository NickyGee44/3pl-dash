import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { AuditRunSummary } from '../types'
import './AuditRunsList.css'

export default function AuditRunsList() {
  const [audits, setAudits] = useState<AuditRunSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAudits()
  }, [])

  const loadAudits = async () => {
    try {
      const response = await api.get('/audits/')
      setAudits(response.data)
    } catch (error) {
      console.error('Error loading audits:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const getStatusBadge = (status: string) => {
    const statusClass = `status-badge status-${status}`
    return <span className={statusClass}>{status}</span>
  }

  if (loading) {
    return <div className="loading">Loading audit runs...</div>
  }

  return (
    <div className="audit-runs-list">
      <div className="page-header">
        <h1>Audit Runs</h1>
        <Link to="/audits/new" className="btn btn-primary">
          New Audit
        </Link>
      </div>

      {audits.length === 0 ? (
        <div className="empty-state">
          <p>No audit runs yet. Create your first audit to get started.</p>
          <Link to="/audits/new" className="btn btn-primary">
            Create Audit
          </Link>
        </div>
      ) : (
        <table className="audits-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Name</th>
              <th>Period</th>
              <th>Status</th>
              <th>Shipments</th>
              <th>Total Spend</th>
              <th>Potential Savings</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {audits.map((audit) => (
              <tr key={audit.id}>
                <td>{audit.customer_name}</td>
                <td>{audit.name}</td>
                <td>{audit.label || '-'}</td>
                <td>{getStatusBadge(audit.status)}</td>
                <td>{audit.shipment_count.toLocaleString()}</td>
                <td>{formatCurrency(audit.total_spend)}</td>
                <td>{formatCurrency(audit.theoretical_savings)}</td>
                <td>{new Date(audit.created_at).toLocaleDateString()}</td>
                <td>
                  <Link to={`/audits/${audit.id}`} className="btn btn-sm">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

