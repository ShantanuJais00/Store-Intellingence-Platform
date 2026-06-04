import React from 'react';
import { AnomalyData } from '../types';
import { Bell, Info, AlertTriangle, ShieldAlert, CheckCircle } from 'lucide-react';

interface AnomalyFeedProps {
  anomalies: AnomalyData | null;
}

const getSeverityIcon = (severity: string) => {
  switch (severity.toUpperCase()) {
    case 'INFO': return <Info className="w-4 h-4 text-blue-400" />;
    case 'WARN': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    case 'CRITICAL': return <ShieldAlert className="w-4 h-4 text-red-500 animate-pulse" />;
    default: return <Info className="w-4 h-4 text-gray-400" />;
  }
};

const getSeverityBg = (severity: string) => {
  switch (severity.toUpperCase()) {
    case 'INFO': return 'bg-blue-500/10 border-blue-500/20';
    case 'WARN': return 'bg-amber-500/10 border-amber-500/20';
    case 'CRITICAL': return 'bg-red-500/10 border-red-500/30';
    default: return 'bg-gray-500/10 border-gray-500/20';
  }
};

const formatTime = (isoString: string) => {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return isoString;
  }
};

const AnomalyFeed: React.FC<AnomalyFeedProps> = ({ anomalies }) => {
  const hasAnomalies = anomalies && anomalies.anomalies.length > 0;

  return (
    <div className="glass-panel rounded-2xl p-6 h-full flex flex-col max-h-[800px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-brand-text" />
          <h2 className="text-xl font-semibold text-white">Live Anomalies</h2>
        </div>
        {hasAnomalies && (
          <span className="bg-brand-danger/20 text-brand-danger text-xs font-bold px-2 py-1 rounded-full animate-pulse">
            {anomalies.anomalies.length} Active
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-4">
        {!hasAnomalies ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="w-16 h-16 rounded-full bg-brand-success/10 flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-brand-success" />
            </div>
            <div>
              <h3 className="text-white font-medium">System Normal</h3>
              <p className="text-sm text-brand-muted mt-1">No anomalies detected in the store environment.</p>
            </div>
          </div>
        ) : (
          anomalies.anomalies.map((anomaly, idx) => (
            <div 
              key={`${anomaly.anomaly_id}-${idx}`}
              className={`p-4 rounded-xl border animate-slide-down flex flex-col gap-2 shadow-lg backdrop-blur-md ${getSeverityBg(anomaly.severity)}`}
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  {getSeverityIcon(anomaly.severity)}
                  <span className="font-bold text-sm tracking-wider text-white">
                    {anomaly.type.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="text-xs text-brand-muted">{formatTime(anomaly.detected_at)}</span>
              </div>
              <p className="text-sm text-gray-300 mt-1 leading-relaxed">
                {anomaly.message}
              </p>
              <div className="mt-2 pt-2 border-t border-white/5">
                <p className="text-xs font-medium text-brand-secondary/80">
                  <span className="uppercase tracking-wider opacity-60 mr-1 text-[10px]">Action:</span> 
                  {anomaly.suggested_action}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AnomalyFeed;
