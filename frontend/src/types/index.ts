export interface Customer {
  id: string
  name: string
  contact_name?: string
  contact_email?: string
  created_at: string
}

export interface AuditRun {
  id: string
  customer_id: string
  name: string
  label?: string
  status: 'created' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  summary_metrics?: {
    shipment_count?: number
    total_spend?: number
    avg_cost_per_shipment?: number
    avg_cost_per_lb?: number
    avg_cost_per_pallet?: number
    carrier_savings_total?: number
    consolidation_savings_total?: number
    total_opportunity?: number
    theoretical_savings?: number
    consolidation_groups?: ConsolidationOpportunity[]
  }
}

export interface AuditRunSummary {
  id: string
  customer_name: string
  name: string
  label?: string
  status: string
  created_at: string
  shipment_count: number
  total_spend?: number
  theoretical_savings?: number
  carrier_savings_total?: number
  consolidation_savings_total?: number
  total_opportunity?: number
}

export interface SourceFile {
  id: string
  audit_run_id: string
  original_filename: string
  file_type: string
  inferred_source_type?: string
  created_at: string
  inferred_mappings?: Record<string, string>
  inferred_mapping_details?: ColumnMapping[]
  low_confidence_columns?: string[]
  columns?: string[]
}

export interface ColumnMapping {
  source_column: string
  target_field: string
  confidence?: number
  needs_review?: boolean
  method?: string
  reason?: string
}

export interface LaneStat {
  id: string
  origin_dc: string
  dest_province?: string
  dest_region?: string
  dest_city?: string
  shipment_count: number
  total_spend: number
  total_weight: number
  total_pallets: number
  avg_cost_per_lb?: number
  avg_cost_per_pallet?: number
  theoretical_best_spend?: number
  theoretical_savings?: number
  savings_pct?: number
}

export interface Exception {
  shipment_id: string
  shipment_ref?: string
  origin_dc?: string
  dest_city?: string
  dest_province?: string
  weight?: number
  pallets?: number
  actual_charge?: number
  cost_per_lb?: number
  flags: string[]
}

export interface Tariff {
  id: string
  carrier_name: string
  origin_dc: string
  tariff_type: 'cwt' | 'skid_spot'
  effective_from?: string
  effective_to?: string
  created_at: string
  lane_count?: number
  break_count?: number
}

export interface ConsolidationOpportunity {
  origin_dc: string
  dest_city: string
  dest_province: string
  ship_date: string
  shipment_count: number
  actual_sum: number
  individual_best_sum: number
  consolidated_charge: number
  incremental_savings: number
  carrier?: string | null
}

export interface AuditReportContext {
  audit: {
    id: string
    name: string
    label?: string
    customer?: string
    status: string
    created_at: string
  }
  totals: {
    shipments: number
    spend: number
    weight: number
    pallets: number
    avg_cost_per_shipment: number
  }
  carrier_optimization: {
    savings?: number | null
    best_charge_total?: number | null
    opportunity_pct?: number | null
  }
  consolidation: {
    savings?: number | null
    opportunities?: ConsolidationOpportunity[]
  }
  total_opportunity?: number | null
  dc_breakdown: Array<{
    origin_dc: string
    shipments: number
    spend: number
    weight: number
  }>
  region_breakdown: Array<{
    region: string
    shipments: number
    spend: number
    weight: number
  }>
  top_lanes_by_spend: Array<{
    origin_dc: string
    destination: string
    total_spend?: number | null
    shipments: number
    savings?: number | null
  }>
  top_lanes_by_savings: Array<{
    origin_dc: string
    destination: string
    savings?: number | null
    savings_pct?: number | null
  }>
  exceptions: {
    total: number
    zero_charge: number
    dim_heavy: number
  }
  generated_at: string
}
