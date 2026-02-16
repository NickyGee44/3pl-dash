import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { Customer, SourceFile, ColumnMapping } from '../types'
import './NewAuditWizard.css'
import * as XLSX from 'xlsx'

type Step = 'customer' | 'files' | 'mappings' | 'processing'

type UploadCategory = 'shipment' | 'rates'

interface SheetOption {
  id: string
  fileKey: string
  originalFile: File
  sheetName?: string
  displayName: string
  selected: boolean
  category: UploadCategory
}

const REQUIRED_MAPPING_GROUPS = [
  { label: 'Origin City', targets: ['origin_city'] },
  { label: 'Origin Province', targets: ['origin_province'] },
  { label: 'Destination City', targets: ['dest_city'] },
  { label: 'Destination Province', targets: ['dest_province'] },
  { label: 'Charge', targets: ['charge'] },
  { label: 'Weight (Scale/Billed/Dim)', targets: ['weight', 'billed_weight', 'dim_weight'] },
]

const normalizedFieldOptions = [
  { value: '', label: 'Unmapped' },
  { value: 'shipment_ref', label: 'Shipment Reference' },
  { value: 'origin_dc', label: 'Origin DC' },
  { value: 'origin_city', label: 'Origin City' },
  { value: 'origin_province', label: 'Origin Province' },
  { value: 'origin_postal', label: 'Origin Postal' },
  { value: 'origin_name', label: 'Origin Name' },
  { value: 'origin_address', label: 'Origin Address' },
  { value: 'dest_city', label: 'Destination City' },
  { value: 'dest_province', label: 'Destination Province' },
  { value: 'dest_postal', label: 'Destination Postal' },
  { value: 'dest_country', label: 'Destination Country' },
  { value: 'dest_name', label: 'Destination Name' },
  { value: 'dest_address', label: 'Destination Address' },
  { value: 'dest_region', label: 'Destination Region' },
  { value: 'ship_date', label: 'Ship Date' },
  { value: 'pallets', label: 'Pallets' },
  { value: 'weight', label: 'Scale Weight' },
  { value: 'billed_weight', label: 'Billed Weight' },
  { value: 'dim_weight', label: 'Dim Weight' },
  { value: 'charge', label: 'Actual Charge' },
  { value: 'carrier', label: 'Carrier' },
  { value: 'customer_ref', label: 'Customer Reference' },
  { value: 'std_transit_days', label: 'Std Transit Days' },
  { value: 'actual_transit_days', label: 'Actual Transit Days' },
  { value: 'pod_signed', label: 'POD Signed' },
  { value: 'pod_signature', label: 'POD Signature' },
]

export default function NewAuditWizard() {
  const [step, setStep] = useState<Step>('customer')
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('')
  const [customerName, setCustomerName] = useState<string>('')
  const [isNewCustomer, setIsNewCustomer] = useState<boolean>(true)
  const [auditName, setAuditName] = useState('')
  const [auditLabel, setAuditLabel] = useState('')
  const [auditRunId, setAuditRunId] = useState<string | null>(null)
  const [sheetOptions, setSheetOptions] = useState<SheetOption[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<SourceFile[]>([])
  const [mappings, setMappings] = useState<Record<string, ColumnMapping[]>>({})
  const [processing, setProcessing] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [progressLabel, setProgressLabel] = useState<string | null>(null)
  const navigate = useNavigate()
  const workbookCache = useRef<Map<string, XLSX.WorkBook>>(new Map())

  useEffect(() => {
    loadCustomers()
  }, [])

  const loadCustomers = async () => {
    try {
      const response = await api.get('/customers/')
      setCustomers(response.data)
    } catch (error) {
      console.error('Error loading customers:', error)
    }
  }

  const handleCreateAudit = async () => {
    if (!auditName) {
      alert('Please enter an audit name')
      return
    }

    try {
      let customerId = selectedCustomerId

      // If creating a new customer, create it first
      if (isNewCustomer && customerName.trim()) {
        try {
          const customerResponse = await api.post('/customers/', {
            name: customerName.trim(),
          })
          customerId = customerResponse.data.id
          if (!customerId) {
            alert('Failed to create customer: No customer ID returned')
            return
          }
        } catch (customerError: any) {
          console.error('Error creating customer:', customerError)
          const customerErrorMsg = customerError.response?.data?.detail || customerError.message || 'Failed to create customer'
          alert(`Failed to create customer: ${customerErrorMsg}`)
          return
        }
      } else if (!selectedCustomerId) {
        alert('Please select a customer or enter a new customer name')
        return
      }

      if (!customerId) {
        alert('Customer ID is missing. Please try again.')
        return
      }

      console.log('Creating audit with:', { customer_id: customerId, name: auditName, label: auditLabel || undefined })
      
      const response = await api.post('/audits/', {
        customer_id: customerId,
        name: auditName,
        label: auditLabel || undefined,
      })
      setAuditRunId(response.data.id)
      setStep('files')
    } catch (error: any) {
      console.error('Error creating audit:', error)
      console.error('Error response:', error.response)
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to create audit run'
      alert(`Failed to create audit run: ${errorMsg}`)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) {
      setSheetOptions([])
      return
    }

    const newOptions: SheetOption[] = []
    const cache = new Map<string, XLSX.WorkBook>()

    for (const file of Array.from(e.target.files)) {
      const fileKey = `${file.name}_${file.lastModified}`
      const extension = file.name.split('.').pop()?.toLowerCase()

      if (extension === 'xlsx' || extension === 'xls') {
        const arrayBuffer = await file.arrayBuffer()
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })
        cache.set(fileKey, workbook)

        workbook.SheetNames.forEach((sheetName) => {
          newOptions.push({
            id: `${fileKey}_${sheetName}`,
            fileKey,
            originalFile: file,
            sheetName,
            displayName: `${file.name} → ${sheetName}`,
            selected: true,
            category: 'shipment',
          })
        })
      } else {
        newOptions.push({
          id: fileKey,
          fileKey,
          originalFile: file,
          displayName: file.name,
          selected: true,
          category: file.name.toLowerCase().includes('rate') ? 'rates' : 'shipment',
        })
      }
    }

    workbookCache.current = cache
    setSheetOptions(newOptions)
  }

  const handleMappingChange = (fileId: string, index: number, value: string) => {
    setMappings((prev) => {
      const existing = prev[fileId] ? [...prev[fileId]] : []
      if (existing[index]) {
        existing[index] = {
          ...existing[index],
          target_field: value,
          confidence: value ? 1 : 0,
          needs_review: !value,
          method: value ? 'manual' : 'unmapped',
          reason: value ? 'Manually confirmed in review.' : 'No mapping selected.',
        }
      }
      return {
        ...prev,
        [fileId]: existing,
      }
    })
  }

  const handleUploadFiles = async () => {
    if (!auditRunId) return

    const selections = sheetOptions.filter((option) => option.selected)
    if (selections.length === 0) {
      alert('Select at least one file or sheet to upload')
      return
    }

    setUploading(true)
    setUploadProgress(0)
    setProgressLabel('Uploading and parsing files...')

    const formData = new FormData()

    const totalSelections = selections.length
    let completed = 0

    for (const option of selections) {
      let uploadFile: File

      if (option.sheetName) {
        let workbook = workbookCache.current.get(option.fileKey)
        if (!workbook) {
          const data = await option.originalFile.arrayBuffer()
          workbook = XLSX.read(data, { type: 'array' })
          workbookCache.current.set(option.fileKey, workbook)
        }

        const worksheet = workbook?.Sheets[option.sheetName]
        if (!worksheet) {
          console.warn(`Sheet ${option.sheetName} not found in ${option.displayName}`)
          continue
        }

        const csv = XLSX.utils.sheet_to_csv(worksheet)
        const safeSheet = option.sheetName.replace(/[^\w\d]+/g, '_')
        const baseName = option.originalFile.name.replace(/\.[^/.]+$/, '')
        uploadFile = new File(
          [csv],
          `${option.category}-${baseName}-${safeSheet}.csv`,
          { type: 'text/csv' }
        )
      } else {
        const arrayBuffer = await option.originalFile.arrayBuffer()
        uploadFile = new File(
          [arrayBuffer],
          `${option.category}-${option.originalFile.name}`,
          { type: option.originalFile.type || 'text/csv' }
        )
      }

      formData.append('files', uploadFile)

      completed += 1
      setUploadProgress(Math.round((completed / totalSelections) * 100))
    }

    try {
      const response = await api.post(`/files/${auditRunId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUploadedFiles(response.data)
      await loadMappings(response.data)
      setStep('mappings')
    } catch (error) {
      console.error('Error uploading files:', error)
      alert('Failed to upload files')
    } finally {
      setUploading(false)
      setProgressLabel(null)
      setUploadProgress(0)
    }
  }

  const loadMappings = async (files: SourceFile[]) => {
    const newMappings: Record<string, ColumnMapping[]> = {}
    for (const file of files) {
      try {
        const response = await api.get<SourceFile>(`/files/${file.id}/mappings`)
        const inferred = response.data.inferred_mappings || {}
        const details = response.data.inferred_mapping_details || []
        const detailByColumn = new Map(details.map((detail) => [detail.source_column, detail]))
        const columns =
          response.data.columns && response.data.columns.length > 0
            ? response.data.columns
            : details.length > 0
              ? details.map((detail) => detail.source_column)
              : Object.keys(inferred)

        newMappings[file.id] = columns.map((column) => ({
          source_column: column,
          target_field: detailByColumn.get(column)?.target_field || inferred[column] || '',
          confidence:
            detailByColumn.get(column)?.confidence ??
            (inferred[column] ? 1 : 0),
          needs_review:
            detailByColumn.get(column)?.needs_review ??
            !Boolean(detailByColumn.get(column)?.target_field || inferred[column]),
          method:
            detailByColumn.get(column)?.method ??
            (inferred[column] ? 'legacy' : 'unmapped'),
          reason: detailByColumn.get(column)?.reason,
        }))
      } catch (error) {
        console.error(`Error loading mappings for file ${file.id}:`, error)
      }
    }
    setMappings(newMappings)
  }

  const handleNormalizeAndRun = async () => {
    if (!auditRunId) return

    const getMissingRequiredLabels = (fileMappings: ColumnMapping[]): string[] => {
      const mappedTargets = new Set(
        fileMappings
          .map((mapping) => mapping.target_field)
          .filter((target): target is string => Boolean(target))
      )
      return REQUIRED_MAPPING_GROUPS
        .filter((group) => !group.targets.some((target) => mappedTargets.has(target)))
        .map((group) => group.label)
    }

    for (const file of uploadedFiles) {
      const fileMappings = mappings[file.id] || []
      const missingLabels = getMissingRequiredLabels(fileMappings)
      if (missingLabels.length > 0) {
        alert(
          `Cannot run audit yet. ${file.original_filename} is missing required mappings: ${missingLabels.join(', ')}.`
        )
        return
      }
    }

    setProcessing(true)
    setProgressLabel('Normalizing files and running audit...')
    setUploadProgress(30)
    setStep('processing')

    try {
      // Normalize each file
      for (const file of uploadedFiles) {
        const fileMappings = (mappings[file.id] || []).filter((mapping) => mapping.target_field)
        await api.post(`/files/${file.id}/normalize`, {
          file_id: file.id,
          mappings: fileMappings,
        })
      }

      setUploadProgress(70)

      // Run audit
      await api.post(`/audits/${auditRunId}/run`)

      // Navigate to detail view
      navigate(`/audits/${auditRunId}`)
    } catch (error) {
      console.error('Error processing audit:', error)
      alert('Failed to process audit')
      setProcessing(false)
      setProgressLabel(null)
      setUploadProgress(0)
    }
  }

  return (
    <div className="new-audit-wizard">
      <div className="wizard-header">
        <h1>Create New Audit</h1>
        <p className="wizard-subtitle">Follow these simple steps to analyze your freight data</p>
      </div>

      {(uploading || processing) && (
        <div className="wizard-progress">
          <div className="wizard-progress-bar">
            <div
              className="wizard-progress-fill"
              style={{ width: `${uploadProgress || (processing ? 90 : 10)}%` }}
            />
          </div>
          {progressLabel && <div className="wizard-progress-label">{progressLabel}</div>}
        </div>
      )}

      <div className="wizard-steps">
        <div className={`step ${step === 'customer' ? 'active' : ['files', 'mappings', 'processing'].includes(step) ? 'completed' : ''}`}>
          <span className="step-number">1</span>
          <span className="step-label">Basic Info</span>
        </div>
        <div className={`step ${step === 'files' ? 'active' : ['mappings', 'processing'].includes(step) ? 'completed' : ''}`}>
          <span className="step-number">2</span>
          <span className="step-label">Upload Data</span>
        </div>
        <div className={`step ${step === 'mappings' ? 'active' : step === 'processing' ? 'completed' : ''}`}>
          <span className="step-number">3</span>
          <span className="step-label">Review</span>
        </div>
        <div className={`step ${step === 'processing' ? 'active' : ''}`}>
          <span className="step-number">4</span>
          <span className="step-label">Analyzing</span>
        </div>
      </div>

      {step === 'customer' && (
        <div className="wizard-content">
          <div className="form-group">
            <label>Customer Selection</label>
            <div className="customer-toggle">
              <button
                type="button"
                className={`toggle-btn ${isNewCustomer ? 'active' : ''}`}
                onClick={() => {
                  setIsNewCustomer(true)
                  setSelectedCustomerId('')
                }}
              >
                New Customer
              </button>
              <button
                type="button"
                className={`toggle-btn ${!isNewCustomer ? 'active' : ''}`}
                onClick={() => {
                  setIsNewCustomer(false)
                  setCustomerName('')
                }}
              >
                Existing Customer
              </button>
            </div>
          </div>

          {isNewCustomer ? (
            <div className="form-group">
              <label>Customer Name *</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g., Global Industrial"
                autoFocus
              />
            </div>
          ) : (
            <div className="form-group">
              <label>Select Customer *</label>
              <select
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
              >
                <option value="">Select a customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="form-group">
            <label>Audit Name *</label>
            <input
              type="text"
              value={auditName}
              onChange={(e) => setAuditName(e.target.value)}
              placeholder="e.g., Global Industrial Q4 2024"
            />
          </div>

          <div className="form-group">
            <label>Period/Label</label>
            <input
              type="text"
              value={auditLabel}
              onChange={(e) => setAuditLabel(e.target.value)}
              placeholder="e.g., July–Dec 2024"
            />
          </div>

          <button onClick={handleCreateAudit} className="btn btn-primary">
            Continue
          </button>
        </div>
      )}

      {step === 'files' && (
        <div className="wizard-content">
          <div className="form-group">
            <label>Upload Files (XLSX, CSV)</label>
            <input
              type="file"
              multiple
              accept=".xlsx,.csv"
              onChange={handleFileSelect}
            />
            {sheetOptions.length > 0 && (
              <div className="sheet-selection-list">
                {sheetOptions.map((option) => (
                  <div key={option.id} className="sheet-selection-row">
                    <label>
                      <input
                        type="checkbox"
                        checked={option.selected}
                        onChange={(evt) => {
                          const updated = sheetOptions.map((opt) =>
                            opt.id === option.id ? { ...opt, selected: evt.target.checked } : opt
                          )
                          setSheetOptions(updated)
                        }}
                      />
                      <span>{option.displayName}</span>
                    </label>
                    <select
                      value={option.category}
                      onChange={(evt) => {
                        const updated = sheetOptions.map((opt) =>
                          opt.id === option.id ? { ...opt, category: evt.target.value as UploadCategory } : opt
                        )
                        setSheetOptions(updated)
                      }}
                    >
                      <option value="shipment">Shipment Data</option>
                      <option value="rates">Rates</option>
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleUploadFiles}
            disabled={sheetOptions.length === 0 || uploading || processing}
            className="btn btn-primary"
          >
            {uploading ? 'Uploading...' : 'Upload & Continue'}
          </button>
        </div>
      )}

      {step === 'mappings' && (
        <div className="wizard-content">
          <p>Review and adjust column mappings. Any row marked as needing review is not fully certain and should be confirmed.</p>
          {uploadedFiles.map((file) => (
            <div key={file.id} className="mapping-section">
              <h3>{file.original_filename}</h3>
              <p className="mapping-summary">
                {(mappings[file.id] || []).filter((mapping) => mapping.needs_review || !mapping.target_field).length} column(s) need review
              </p>
              {(mappings[file.id] || []).length === 0 ? (
                <div className="mapping-empty">
                  No columns were detected for this tab. It may be a summary/analysis tab rather than row-level shipment data.
                </div>
              ) : (
                <table className="mappings-table">
                  <thead>
                    <tr>
                      <th>Source Column</th>
                      <th>Target Field</th>
                      <th>Confidence</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mappings[file.id]?.map((mapping, idx) => (
                      <tr
                        key={idx}
                        className={mapping.needs_review || !mapping.target_field ? 'needs-review' : 'confirmed'}
                      >
                        <td>
                          <div>{mapping.source_column}</div>
                          {mapping.reason && <div className="mapping-reason">{mapping.reason}</div>}
                        </td>
                        <td>
                          <select
                            value={mapping.target_field}
                            onChange={(e) => handleMappingChange(file.id, idx, e.target.value)}
                          >
                            {normalizedFieldOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="mapping-confidence">
                          {mapping.target_field ? `${Math.round((mapping.confidence || 0) * 100)}%` : '—'}
                        </td>
                        <td>
                          <span
                            className={`mapping-status ${mapping.needs_review || !mapping.target_field ? 'review' : 'ok'}`}
                          >
                            {mapping.needs_review || !mapping.target_field ? 'Needs review' : 'Confirmed'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ))}

          <button onClick={handleNormalizeAndRun} className="btn btn-primary" disabled={processing}>
            {processing ? 'Processing...' : 'Process & Run Audit'}
          </button>
        </div>
      )}

      {step === 'processing' && (
        <div className="wizard-content">
          <div className="processing-message">
            <div className="spinner"></div>
            <p>Processing files and running audit...</p>
          </div>
        </div>
      )}
    </div>
  )
}
