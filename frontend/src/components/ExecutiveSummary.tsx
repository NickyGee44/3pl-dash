import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import './ExecutiveSummary.css'

interface ExecutiveSummaryProps {
  audit: any
  lanes: any[]
  exceptions: any[]
}

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe']

const formatMoney = (value?: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0)

export default function ExecutiveSummary({ audit, lanes, exceptions }: ExecutiveSummaryProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'lanes' | 'savings'>('overview')

  const metrics = audit.summary_metrics || {}
  const totalSpend = metrics.total_spend || 0
  const carrierSavings = metrics.carrier_savings_total || 0
  const consolidationSavings = metrics.consolidation_savings_total || 0
  const totalOpportunity = metrics.total_opportunity || carrierSavings + consolidationSavings
  const fallbackLaneSavings = lanes.reduce((sum, lane) => sum + (lane.theoretical_savings || 0), 0)
  const opportunityValue = totalOpportunity || fallbackLaneSavings
  const savingsPercent = totalSpend > 0 ? (opportunityValue / totalSpend) * 100 : 0

  // Prepare data for charts
  const topLanesBySpend = [...lanes]
    .sort((a, b) => b.total_spend - a.total_spend)
    .slice(0, 10)
    .map(lane => ({
      name: `${lane.origin_dc} → ${lane.dest_province || lane.dest_region || 'Unknown'}`,
      spend: lane.total_spend,
      savings: lane.theoretical_savings || 0,
    }))

  const topLanesBySavings = [...lanes]
    .filter(l => l.theoretical_savings && l.theoretical_savings > 0)
    .sort((a, b) => (b.theoretical_savings || 0) - (a.theoretical_savings || 0))
    .slice(0, 10)
    .map(lane => ({
      name: `${lane.origin_dc} → ${lane.dest_province || lane.dest_region || 'Unknown'}`,
      savings: lane.theoretical_savings,
      percent: lane.savings_pct || 0,
    }))

  const lanesWithSavings = lanes.filter(l => l.theoretical_savings).length || 1

  const spendByDC = lanes.reduce((acc, lane) => {
    const dc = lane.origin_dc || 'Unknown'
    acc[dc] = (acc[dc] || 0) + lane.total_spend
    return acc
  }, {} as Record<string, number>)

  const dcChartData = Object.entries(spendByDC).map(([name, value]) => ({
    name,
    value: Math.round(value),
  }))

  return (
    <div className="executive-summary">
      {/* Key Metrics Banner */}
      <div className="summary-banner">
        <div className="banner-metric">
          <div className="banner-label">Total Spend</div>
          <div className="banner-value">{formatMoney(totalSpend)}</div>
        </div>
        <div className="banner-metric">
          <div className="banner-label">Carrier Optimization</div>
          <div className="banner-value savings">{formatMoney(carrierSavings)}</div>
          <div className="banner-sublabel">vs actual charges</div>
        </div>
        <div className="banner-metric">
          <div className="banner-label">Consolidation Savings</div>
          <div className="banner-value savings">{formatMoney(consolidationSavings)}</div>
          <div className="banner-sublabel">Same-day & destination</div>
        </div>
        <div className="banner-metric highlight">
          <div className="banner-label">Total Opportunity</div>
          <div className="banner-value savings">{formatMoney(opportunityValue)}</div>
          <div className="banner-sublabel">{savingsPercent.toFixed(1)}% of spend</div>
        </div>
        <div className="banner-metric">
          <div className="banner-label">Shipments</div>
          <div className="banner-value">{metrics.shipment_count?.toLocaleString() || 0}</div>
        </div>
        <div className="banner-metric">
          <div className="banner-label">Lanes Analyzed</div>
          <div className="banner-value">{lanes.length}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="summary-tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={activeTab === 'lanes' ? 'active' : ''}
          onClick={() => setActiveTab('lanes')}
        >
          Top Lanes
        </button>
        <button
          className={activeTab === 'savings' ? 'active' : ''}
          onClick={() => setActiveTab('savings')}
        >
          Savings Opportunities
        </button>
      </div>

      {/* Tab Content */}
      <div className="summary-content">
        {activeTab === 'overview' && (
          <div className="overview-grid">
            <div className="chart-card">
              <h3>Spend by Distribution Center</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={dcChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {dcChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Top 10 Lanes by Spend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topLanesBySpend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    angle={-45}
                    textAnchor="end"
                    height={100}
                    fontSize={12}
                  />
                  <YAxis />
                  <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
                  <Bar dataKey="spend" fill="#667eea" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="insights-card">
              <h3>Key Insights</h3>
              <ul className="insights-list">
                <li>
                  <strong>{lanes.length}</strong> unique lanes identified
                </li>
                <li>
                  <strong>{exceptions.length}</strong> exceptions requiring review
                </li>
                <li>
                  Average cost per shipment: <strong>{formatMoney(totalSpend / (metrics.shipment_count || 1))}</strong>
                </li>
                {opportunityValue > 0 && (
                  <li className="highlight-insight">
                    Potential savings of <strong>{formatMoney(opportunityValue)}</strong> identified
                  </li>
                )}
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'lanes' && (
          <div className="lanes-table-container">
            <table className="executive-table">
              <thead>
                <tr>
                  <th>Lane</th>
                  <th>Shipments</th>
                  <th>Total Spend</th>
                  <th>Avg Cost/LB</th>
                  <th>Potential Savings</th>
                  <th>Savings %</th>
                </tr>
              </thead>
              <tbody>
                {topLanesBySpend.map((lane, idx) => {
                  const fullLane = lanes.find(l => 
                    `${l.origin_dc} → ${l.dest_province || l.dest_region || 'Unknown'}` === lane.name
                  )
                  return (
                    <tr key={idx}>
                      <td><strong>{lane.name}</strong></td>
                      <td>{fullLane?.shipment_count.toLocaleString() || '-'}</td>
                      <td>${lane.spend.toLocaleString()}</td>
                      <td>${fullLane?.avg_cost_per_lb?.toFixed(4) || '-'}</td>
                      <td className={fullLane?.theoretical_savings ? 'savings-cell' : ''}>
                        {fullLane?.theoretical_savings ? `$${fullLane.theoretical_savings.toLocaleString()}` : '-'}
                      </td>
                      <td className={fullLane?.savings_pct ? 'savings-cell' : ''}>
                        {fullLane?.savings_pct ? `${fullLane.savings_pct.toFixed(1)}%` : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'savings' && (
          <div className="savings-view">
            <div className="chart-card full-width">
              <h3>Top 10 Savings Opportunities</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={topLanesBySavings} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={150} fontSize={12} />
                  <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
                  <Bar dataKey="savings" fill="#2e7d32" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="savings-summary">
              <h3>Savings Summary</h3>
              <div className="savings-stats">
                <div className="savings-stat">
                  <div className="stat-label">Total Potential Savings</div>
                  <div className="stat-value">{formatMoney(opportunityValue)}</div>
                </div>
                <div className="savings-stat">
                  <div className="stat-label">Average Savings per Lane</div>
                  <div className="stat-value">
                    {formatMoney(opportunityValue / lanesWithSavings)}
                  </div>
                </div>
                <div className="savings-stat">
                  <div className="stat-label">Lanes with Savings</div>
                  <div className="stat-value">
                    {lanes.filter(l => l.theoretical_savings && l.theoretical_savings > 0).length}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

