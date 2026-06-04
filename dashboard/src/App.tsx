import { useState } from 'react';
import Header from './components/Header';
import MetricCards from './components/MetricCards';
import HeatmapView from './components/HeatmapView';
import FunnelChart from './components/FunnelChart';
import AnomalyFeed from './components/AnomalyFeed';
import LiveEventTicker from './components/LiveEventTicker';
import { useWebSocket } from './hooks/useWebSocket';
import { useStoreMetrics } from './hooks/useStoreMetrics';
import { Loader2, AlertCircle } from 'lucide-react';

function App() {
  const [storeId, setStoreId] = useState('ST1076');
  const { isConnected, events } = useWebSocket('ws://localhost:8000/ws');
  const { metrics, funnel, heatmap, anomalies, loading, error } = useStoreMetrics(storeId);

  return (
    <div className="min-h-screen bg-brand-background text-brand-text flex flex-col relative pb-10">
      <Header storeId={storeId} setStoreId={setStoreId} isConnected={isConnected} />
      
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {error && (
          <div className="bg-brand-danger/20 border border-brand-danger/50 text-brand-danger p-4 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5" />
            <p>Error loading dashboard data: {error}</p>
          </div>
        )}
        
        {loading && !metrics ? (
          <div className="flex-1 flex items-center justify-center min-h-[50vh]">
            <div className="flex flex-col items-center gap-4 text-brand-primary">
              <Loader2 className="w-12 h-12 animate-spin" />
              <p className="text-lg font-medium text-brand-text">Initializing Intelligence Platform...</p>
            </div>
          </div>
        ) : (
          <>
            <MetricCards metrics={metrics} anomalyCount={anomalies?.anomalies.length || 0} />
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <HeatmapView heatmap={heatmap} />
                <FunnelChart funnel={funnel} />
              </div>
              <div className="lg:col-span-1">
                <AnomalyFeed anomalies={anomalies} />
              </div>
            </div>
          </>
        )}
      </main>

      <LiveEventTicker events={events} />
    </div>
  );
}

export default App;
