import { useState, useEffect, useCallback } from 'react';
import { Metrics, FunnelData, HeatmapData, AnomalyData } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

export const useStoreMetrics = (storeId: string) => {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [metricsRes, funnelRes, heatmapRes, anomaliesRes] = await Promise.all([
        fetch(`${API_BASE}/stores/${storeId}/metrics`),
        fetch(`${API_BASE}/stores/${storeId}/funnel`),
        fetch(`${API_BASE}/stores/${storeId}/heatmap`),
        fetch(`${API_BASE}/stores/${storeId}/anomalies`),
      ]);

      if (!metricsRes.ok) throw new Error("Failed to fetch metrics");
      if (!funnelRes.ok) throw new Error("Failed to fetch funnel");
      if (!heatmapRes.ok) throw new Error("Failed to fetch heatmap");
      if (!anomaliesRes.ok) throw new Error("Failed to fetch anomalies");

      setMetrics(await metricsRes.json());
      setFunnel(await funnelRes.json());
      setHeatmap(await heatmapRes.json());
      setAnomalies(await anomaliesRes.json());
    } catch (err: any) {
      setError(err.message || 'Error fetching data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    fetchData();
    // Refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { metrics, funnel, heatmap, anomalies, loading, error, refetch: fetchData };
};
