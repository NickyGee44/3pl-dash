import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'
import { AuditRun, LaneStat, Exception, AuditReportContext } from '../types'
import ExecutiveSummary from '../components/ExecutiveSummary'
import './AuditDetailView.css'

export default function AuditDetailView() {
  const { id } = useParams<{ id: string }>()
  const [audit, setAudit] = useState<AuditRun | null>(null)
  const [lanes, setLanes] = useState<LaneStat[]>([])
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [loading, setLoading] = useState(true)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)
  const [rerating, setRerating] = useState(false)
  const [reportContext, setReportContext] = useState<AuditReportContext | null>(null)
  const [contextError, setContextError] = useState<string | null>(null)
  const [askInput, setAskInput] = useState('')
  const [askResponse, setAskResponse] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)
  const aiSectionRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (id) {
      loadAudit()
      loadLanes()
      loadExceptions()
      loadReportContext()
    }
  }, [id])

  const loadAudit = async () => {
    if (!id) return
    try {
      const response = await api.get(`/audits/${id}`)
      setAudit(response.data)
    } catch (error) {
      console.error('Error loading audit:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadLanes = async () => {
    if (!id) return
    try {
      const response = await api.get(`/reports/${id}/lanes`)
      setLanes(response.data.lanes)
    } catch (error) {
      console.error('Error loading lanes:', error)
    }
  }

  const loadExceptions = async () => {
    if (!id) return
    try {
      const response = await api.get(`/reports/${id}/exceptions`)
      setExceptions(response.data.exceptions)
    } catch (error) {
      console.error('Error loading exceptions:', error)
    }
  }

  const loadReportContext = async () => {
    if (!id) return
    try {
      const response = await api.get(`/audits/${id}/report-context`)
      setReportContext(response.data.context)
      setContextError(null)
    } catch (error) {
      console.error('Error loading report context:', error)
      setContextError('Unable to load report context.')
    }
  }

  const handleGenerateSummary = async () => {
    if (!id) return
    setGeneratingSummary(true)
    try {
      const response = await api.post(`/reports/${id}/executive-summary`)
      setSummary(response.data.summary)
    } catch (error) {
      console.error('Error generating summary:', error)
      alert('Failed to generate summary')
    } finally {
      setGeneratingSummary(false)
    }
  }

  const handleDownloadExcel = async () => {
    if (!id) return
    try {
      const response = await api.get(`/reports/${id}/excel`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `audit_report_${id}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error downloading Excel:', error)
      alert('Failed to download Excel report')
    }
  }

  const handleDownloadPDF = async () => {
    if (!id) return
    try {
      const response = await api.get(`/reports/${id}/pdf`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `audit_summary_${id}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error downloading PDF:', error)
      alert('Failed to download PDF report')
    }
  }

  const handleRerate = async () => {
    if (!id) return
    setRerating(true)
    try {
      await api.post(`/audits/${id}/rerate`)
      // Reload data to show updated savings
      await loadAudit()
      await loadLanes()
      await loadReportContext()
      alert('Re-rating completed! Savings have been calculated using tariff data.')
    } catch (error) {
      console.error('Error re-rating:', error)
      alert('Failed to re-rate shipments. Make sure tariffs are loaded.')
    } finally {
      setRerating(false)
    }
  }

  const handleAskQuestion = async () => {
    if (!id || !askInput.trim()) return
    setAsking(true)
    setAskResponse(null)
    try {
      const response = await api.post(`/audits/${id}/ask`, { question: askInput.trim() })
      setAskResponse(response.data.answer)
    } catch (error) {
      console.error('Error asking AI:', error)
      alert('Failed to get AI response.')
    } finally {
      setAsking(false)
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  if (loading) {
    return <div className="loading">Loading audit details...</div>
  }

  if (!audit) {
    return <div className="error">Audit not found</div>
  }

  const metrics = audit.summary_metrics || {}

  return (
    <div className="audit-detail-view">
      <div className="detail-header">
        <Link to="/" className="back-link">← Back to Audits</Link>
        <div className="detail-header-main">
          <div>
            <h1>{audit.name}</h1>
            {audit.label && <p className="audit-label">{audit.label}</p>}
          </div>
          <div className="audit-action-bar">
            <div className="action-metrics">
              <div className="action-metric">
                <span>Total Spend</span>
                <strong>{formatCurrency(metrics.total_spend)}</strong>
              </div>
              <div className="action-metric">
                <span>Total Opportunity</span>
                <strong>{formatCurrency(metrics.total_opportunity || metrics.theoretical_savings)}</strong>
              </div>
            </div>
            <div className="action-buttons">
              <button
                onClick={handleRerate}
                disabled={rerating}
                className="btn btn-primary"
              >
                {rerating ? 'Re-rating…' : 'Re-rate with Tariffs'}
              </button>
              <button
                onClick={handleGenerateSummary}
                disabled={generatingSummary}
                className="btn btn-secondary"
              >
                {generatingSummary ? 'Generating…' : 'Generate Executive Summary'}
              </button>
              <button
                onClick={() => {
                  if (aiSectionRef.current) {
                    aiSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }
                }}
                className="btn btn-secondary"
              >
                Ask AI About This Audit
              </button>
            </div>
          </div>
        </div>
      </div>

      {(rerating || generatingSummary) && (
        <div className="audit-progress">
          <div className="audit-progress-bar">
            <div className="audit-progress-fill" />
          </div>
          <div className="audit-progress-label">
            {rerating && 'Re-rating shipments using tariff data…'}
            {generatingSummary && !rerating && 'Generating executive summary with AI…'}
          </div>
        </div>
      )}

      {/* Executive Summary Component */}
      <ExecutiveSummary audit={audit} lanes={lanes} exceptions={exceptions} />

      {reportContext && (
        <div className="opportunity-cards">
          <div className="opportunity-card">
            <span>Carrier Optimization</span>
            <strong>{formatCurrency(reportContext.carrier_optimization.savings || 0)}</strong>
            <small>vs actual charges</small>
          </div>
          <div className="opportunity-card">
            <span>Consolidation Savings</span>
            <strong>{formatCurrency(reportContext.consolidation.savings || 0)}</strong>
            <small>Same-day & destination</small>
          </div>
          <div className="opportunity-card total">
            <span>Total Opportunity</span>
            <strong>{formatCurrency(reportContext.total_opportunity || 0)}</strong>
            <small>{((reportContext.carrier_optimization.opportunity_pct ?? 0)).toFixed(1)}% of spend</small>
          </div>
        </div>
      )}

      {/* Detailed Lanes Section - Collapsible */}
      <div className="lanes-section">
        <details className="section-details">
          <summary className="section-summary">
            <h2>Detailed Lane Statistics</h2>
            <span className="toggle-icon">▼</span>
          </summary>
          <div className="table-container">
            <table className="lanes-table">
              <thead>
                <tr>
                  <th>Origin DC</th>
                  <th>Destination</th>
                  <th>Shipments</th>
                  <th>Total Spend</th>
                  <th>Avg $/LB</th>
                  <th>Theoretical Best</th>
                  <th>Potential Savings</th>
                  <th>Savings %</th>
                </tr>
              </thead>
              <tbody>
                {lanes.map((lane) => (
                  <tr key={lane.id}>
                    <td>{lane.origin_dc}</td>
                    <td>{lane.dest_province || lane.dest_region || lane.dest_city || 'Unknown'}</td>
                    <td>{lane.shipment_count.toLocaleString()}</td>
                    <td>{formatCurrency(lane.total_spend)}</td>
                    <td>{formatCurrency(lane.avg_cost_per_lb)}</td>
                    <td>{formatCurrency(lane.theoretical_best_spend)}</td>
                    <td className={lane.theoretical_savings && lane.theoretical_savings > 0 ? 'savings-positive' : ''}>
                      {formatCurrency(lane.theoretical_savings)}
                    </td>
                    <td className={lane.savings_pct && lane.savings_pct > 0 ? 'savings-positive' : ''}>
                      {lane.savings_pct ? `${lane.savings_pct.toFixed(1)}%` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>

      <div className="exceptions-section">
        <h2>Exceptions</h2>
        <div className="table-container">
          <table className="exceptions-table">
            <thead>
              <tr>
                <th>Shipment Ref</th>
                <th>Origin DC</th>
                <th>Destination</th>
                <th>Charge</th>
                <th>Weight</th>
                <th>Cost/LB</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {exceptions.slice(0, 50).map((exc) => (
                <tr key={exc.shipment_id}>
                  <td>{exc.shipment_ref || '-'}</td>
                  <td>{exc.origin_dc || '-'}</td>
                  <td>{exc.dest_city || exc.dest_province || '-'}</td>
                  <td>{formatCurrency(exc.actual_charge)}</td>
                  <td>{exc.weight?.toLocaleString() || '-'}</td>
                  <td>{formatCurrency(exc.cost_per_lb)}</td>
                  <td>
                    {exc.flags.map((flag, idx) => (
                      <span key={idx} className="flag-badge">{flag}</span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="reports-section">
        <h2>Reports</h2>
        <div className="report-actions">
          <button onClick={handleDownloadExcel} className="btn btn-secondary">
            Download Excel
          </button>
          <button onClick={handleDownloadPDF} className="btn btn-secondary">
            Download PDF
          </button>
        </div>

        {summary && (
          <div className="summary-preview">
            <div className="summary-header">
              <h3>AI-Generated Executive Summary</h3>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setSummary(null)}
              >
                Close
              </button>
            </div>
            <div className="summary-content markdown-content">
              {(() => {
                const lines = summary.split('\n')
                const elements: JSX.Element[] = []
                let currentList: string[] = []
                
                const flushList = () => {
                  if (currentList.length > 0) {
                    elements.push(
                      <ul key={`list-${elements.length}`}>
                        {currentList.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    )
                    currentList = []
                  }
                }
                
                lines.forEach((line, idx) => {
                  const trimmed = line.trim()
                  
                  // Headings
                  if (trimmed.match(/^#{1,3}\s/)) {
                    flushList()
                    const level = trimmed.match(/^#+/)?.[0].length || 1
                    const text = trimmed.replace(/^#+\s*/, '')
                    if (level === 1) {
                      elements.push(<h1 key={idx}>{text}</h1>)
                    } else if (level === 2) {
                      elements.push(<h2 key={idx}>{text}</h2>)
                    } else {
                      elements.push(<h3 key={idx}>{text}</h3>)
                    }
                    return
                  }
                  
                  // List items
                  if (trimmed.match(/^[-*]\s/)) {
                    currentList.push(trimmed.replace(/^[-*]\s*/, ''))
                    return
                  }
                  
                  // Empty lines
                  if (trimmed === '') {
                    flushList()
                    elements.push(<br key={idx} />)
                    return
                  }
                  
                  // Regular paragraphs
                  flushList()
                  elements.push(<p key={idx}>{line}</p>)
                })
                
                flushList() // Flush any remaining list
                return elements
              })()}
            </div>
          </div>
        )}

        {contextError && <div className="context-error">{contextError}</div>}
      </div>

      <div className="ai-analyst-section" ref={aiSectionRef}>
        <h2>Ask AI About This Audit</h2>
        <p>Need a narrative or specific insight? Ask the 3PL analyst and it will respond using the live audit context.</p>
        <textarea
          value={askInput}
          onChange={(e) => setAskInput(e.target.value)}
          placeholder="e.g., Where are the biggest savings between SCARB and CLG? "
        />
        <div className="ai-actions">
          <button
            className="btn btn-primary"
            onClick={handleAskQuestion}
            disabled={asking || !askInput.trim()}
          >
            {asking ? 'Analyzing...' : 'Ask AI'}
          </button>
          {askResponse && (
            <button className="btn btn-secondary" onClick={() => setAskResponse(null)}>
              Clear Response
            </button>
          )}
        </div>
        {askResponse && (
          <div className="ai-response">
            <h3>AI Analyst</h3>
            <div className="ai-response-body">{askResponse}</div>
          </div>
        )}
      </div>
    </div>
  )
}

