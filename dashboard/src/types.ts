export interface Metrics {
  unique_visitors: number;
  conversion_rate: number;
  avg_dwell_per_zone: Record<string, number>;
  queue_depth: number;
  abandonment_rate: number;
}

export interface FunnelStage {
  name: string;
  count: number;
  dropoff_pct: number;
}

export interface FunnelData {
  stages: FunnelStage[];
}

export interface HeatmapZone {
  zone_id: string;
  frequency: number;
  avg_dwell_ms: number;
  normalized_score: number;
  data_confidence: string;
}

export interface HeatmapData {
  zones: HeatmapZone[];
}

export interface Anomaly {
  anomaly_id: string;
  type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL' | string;
  message: string;
  suggested_action: string;
  detected_at: string;
}

export interface AnomalyData {
  anomalies: Anomaly[];
}

export interface LiveEvent {
  event_type: string;
  visitor_id?: string;
  timestamp: string;
  [key: string]: any;
}
