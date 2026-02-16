import { FormEvent, useEffect, useState } from 'react'
import api from '../api/client'
import { Tariff } from '../types'
import './TariffLibrary.css'

const CARRIER_OPTIONS = [
  'APPS',
  'Rosedale',
  'Maritime Ontario',
  'Groupe Guilbault',
  'CFF',
]

export default function TariffLibrary() {
  const [tariffs, setTariffs] = useState<Tariff[]>([])
  const [loading, setLoading] = useState(true)
  const [carrier, setCarrier] = useState(CARRIER_OPTIONS[0])
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTariffs()
  }, [])

  const fetchTariffs = async () => {
    setLoading(true)
    setError(null)
    try {
      // Avoid backend redirect from /api/tariffs -> /api/tariffs/ (can break behind proxies).
      const response = await api.get('/tariffs/')
      setTariffs(response.data)
    } catch (err) {
      console.error('Error loading tariffs', err)
      setError('Failed to load tariffs. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault()
    if (!carrier || !file) {
      setError('Select a carrier and file before uploading.')
      return
    }
    setUploading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post(`/tariffs/ingest?carrier_name=${encodeURIComponent(carrier)}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setFile(null)
      await fetchTariffs()
      const laneCount = response.data?.lane_count
      const breakCount = response.data?.break_count
      if (laneCount != null && breakCount != null) {
        alert(`Tariff ingested for ${carrier} (${laneCount} lanes, ${breakCount} breaks)`)
      } else {
        alert(`Tariff ingested for ${carrier}`)
      }
    } catch (err: any) {
      console.error('Error ingesting tariff', err)
      const detail = err.response?.data?.detail || err.message
      setError(`Failed to ingest tariff: ${detail}`)
    } finally {
      setUploading(false)
    }
  }

  const handleRefreshCache = async () => {
    setRefreshing(true)
    setError(null)
    try {
      await api.post('/tariffs/refresh-cache')
      alert('Tariff cache refreshed')
    } catch (err) {
      console.error('Error refreshing cache', err)
      setError('Failed to refresh tariff cache.')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="tariff-library">
      <header className="tariff-header">
        <div>
          <h1>Tariff Library</h1>
          <p>Upload and manage reusable FAK/spot tariffs for all audits.</p>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={fetchTariffs} disabled={loading}>
            {loading ? 'Refreshing...' : 'Reload'}
          </button>
          <button className="btn btn-secondary" onClick={handleRefreshCache} disabled={refreshing}>
            {refreshing ? 'Refreshing Cache...' : 'Refresh Cache'}
          </button>
        </div>
      </header>

      <section className="tariff-upload">
        <form onSubmit={handleUpload} className="tariff-upload-form">
          <label>
            Carrier
            <select value={carrier} onChange={(e) => setCarrier(e.target.value)}>
              {CARRIER_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="file-input">
            Tariff File (.xlsx)
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>

          <button type="submit" className="btn btn-primary" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Tariff'}
          </button>
        </form>
        <p className="upload-hint">
          Tip: Upload each carrier’s 2025 program once. All audits will share this library when running re-rates or consolidations.
        </p>
        {error && <div className="error-banner">{error}</div>}
      </section>

      <section className="tariff-table-section">
        <div className="table-header">
          <h2>Available Tariffs</h2>
          <span>{tariffs.length} loaded</span>
        </div>
        {loading ? (
          <div className="loading">Loading tariffs...</div>
        ) : tariffs.length === 0 ? (
          <div className="empty-state">No tariffs uploaded yet.</div>
        ) : (
          <div className="table-container">
            <table className="tariff-table">
              <thead>
                <tr>
                  <th>Carrier</th>
                  <th>Origin DC</th>
                  <th>Type</th>
                  <th>Lanes</th>
                  <th>Breaks</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {tariffs.map(tariff => (
                  <tr key={tariff.id}>
                    <td>{tariff.carrier_name}</td>
                    <td>{tariff.origin_dc}</td>
                    <td>{tariff.tariff_type === 'cwt' ? 'CWT' : 'Skid Spot'}</td>
                    <td>{tariff.lane_count ?? '—'}</td>
                    <td>{tariff.break_count ?? '—'}</td>
                    <td>{new Date(tariff.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
