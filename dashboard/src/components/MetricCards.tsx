import React from 'react';
import { Metrics } from '../types';
import { Users, TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react';

interface MetricCardsProps {
  metrics: Metrics | null;
  anomalyCount: number;
}

const MetricCards: React.FC<MetricCardsProps> = ({ metrics, anomalyCount }) => {
  if (!metrics) return null;

  const convRate = metrics.conversion_rate || 0;
  const convColor = convRate > 20 ? 'text-brand-success' : convRate >= 10 ? 'text-brand-warning' : 'text-brand-danger';
  const queueDepth = metrics.queue_depth || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Visitors Card */}
      <div className="glass-card p-5 border-l-4 border-l-brand-primary">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm font-medium text-brand-muted mb-1">Total Visitors</p>
            <h3 className="text-3xl font-bold text-white">{metrics.unique_visitors?.toLocaleString() || 0}</h3>
          </div>
          <div className="p-3 rounded-xl bg-brand-primary/10 text-brand-primary">
            <Users className="w-6 h-6" />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-1 text-sm text-brand-success font-medium">
          <TrendingUp className="w-4 h-4" />
          <span>+12.5%</span>
          <span className="text-brand-muted ml-1">vs last hour</span>
        </div>
      </div>

      {/* Conversion Rate Card */}
      <div className="glass-card p-5 border-l-4 border-l-brand-secondary">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm font-medium text-brand-muted mb-1">Conversion Rate</p>
            <h3 className={`text-3xl font-bold ${convColor}`}>
              {convRate.toFixed(1)}%
            </h3>
          </div>
          <div className="p-3 rounded-xl bg-brand-secondary/10 text-brand-secondary">
            <Activity className="w-6 h-6" />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-1 text-sm text-brand-danger font-medium">
          <TrendingDown className="w-4 h-4" />
          <span>-2.1%</span>
          <span className="text-brand-muted ml-1">vs yesterday</span>
        </div>
      </div>

      {/* Queue Depth Card */}
      <div className={`glass-card p-5 border-l-4 ${queueDepth > 5 ? 'border-l-brand-warning bg-brand-warning/5 animate-pulse' : 'border-l-brand-success'}`}>
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm font-medium text-brand-muted mb-1">Queue Depth</p>
            <h3 className="text-3xl font-bold text-white">{queueDepth}</h3>
          </div>
          <div className={`p-3 rounded-xl ${queueDepth > 5 ? 'bg-brand-warning/10 text-brand-warning' : 'bg-brand-success/10 text-brand-success'}`}>
            <Users className="w-6 h-6" />
          </div>
        </div>
        <div className="mt-4 text-sm text-brand-muted">
          {queueDepth > 5 ? (
            <span className="text-brand-warning font-medium">High wait times</span>
          ) : (
            <span className="text-brand-success font-medium">Optimal flow</span>
          )}
        </div>
      </div>

      {/* Anomalies Card */}
      <div className={`glass-card p-5 border-l-4 ${anomalyCount > 0 ? 'border-l-brand-danger' : 'border-l-brand-success'}`}>
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm font-medium text-brand-muted mb-1">Active Anomalies</p>
            <h3 className="text-3xl font-bold text-white">{anomalyCount}</h3>
          </div>
          <div className={`p-3 rounded-xl ${anomalyCount > 0 ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>
        <div className="mt-4">
          {anomalyCount > 0 ? (
            <span className="inline-flex items-center rounded-full bg-brand-danger/10 px-2.5 py-0.5 text-xs font-medium text-brand-danger">
              Requires attention
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-brand-success/10 px-2.5 py-0.5 text-xs font-medium text-brand-success">
              All clear
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetricCards;
