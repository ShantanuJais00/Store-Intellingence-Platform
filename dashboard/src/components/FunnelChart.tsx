import React from 'react';
import { FunnelData } from '../types';
import { Filter } from 'lucide-react';

interface FunnelChartProps {
  funnel: FunnelData | null;
}

const FunnelChart: React.FC<FunnelChartProps> = ({ funnel }) => {
  if (!funnel || funnel.stages.length === 0) return null;

  const maxCount = Math.max(...funnel.stages.map(s => s.count));

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-8">
        <Filter className="w-5 h-5 text-brand-secondary" />
        <h2 className="text-xl font-semibold text-white">Conversion Funnel</h2>
      </div>

      <div className="flex flex-col items-center w-full max-w-2xl mx-auto space-y-2">
        {funnel.stages.map((stage, index) => {
          // Calculate width percentage relative to max count (100% at top)
          const widthPct = Math.max((stage.count / maxCount) * 100, 20); // Min 20% width
          
          return (
            <div key={stage.name} className="w-full flex flex-col items-center">
              <div 
                className="relative flex items-center justify-between px-6 py-4 transition-all duration-1000 ease-out rounded-lg shadow-lg"
                style={{ 
                  width: `${widthPct}%`,
                  background: `linear-gradient(90deg, rgba(99, 102, 241, ${0.8 - index * 0.15}) 0%, rgba(139, 92, 246, ${0.8 - index * 0.15}) 100%)`,
                  clipPath: index < funnel.stages.length - 1 ? 'polygon(0 0, 100% 0, 95% 100%, 5% 100%)' : 'none'
                }}
              >
                <span className="font-semibold text-white whitespace-nowrap">{stage.name}</span>
                <span className="font-bold text-white text-lg">{stage.count.toLocaleString()}</span>
              </div>
              
              {index < funnel.stages.length - 1 && (
                <div className="flex flex-col items-center my-2">
                  <div className="w-px h-6 bg-white/20"></div>
                  <div className="bg-white/10 px-3 py-1 rounded-full text-xs font-medium text-brand-warning border border-white/5 -my-3 z-10 backdrop-blur-md shadow-lg">
                    {stage.dropoff_pct.toFixed(1)}% dropoff
                  </div>
                  <div className="w-px h-6 bg-white/20"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FunnelChart;
