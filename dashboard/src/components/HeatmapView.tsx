import React from 'react';
import { HeatmapData } from '../types';
import { Map } from 'lucide-react';

interface HeatmapViewProps {
  heatmap: HeatmapData | null;
}

const getHeatColor = (score: number) => {
  // 0 -> cool blue, 50 -> yellow, 100 -> red
  if (score < 33) return `rgba(59, 130, 246, ${score / 33 * 0.8 + 0.2})`; // Blue
  if (score < 66) return `rgba(234, 179, 8, ${(score - 33) / 33 * 0.8 + 0.2})`; // Yellow
  return `rgba(239, 68, 68, ${(score - 66) / 34 * 0.8 + 0.2})`; // Red
};

const HeatmapView: React.FC<HeatmapViewProps> = ({ heatmap }) => {
  if (!heatmap) return null;

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <Map className="w-5 h-5 text-brand-primary" />
        <h2 className="text-xl font-semibold text-white">Store Heatmap</h2>
      </div>
      
      <div className="relative w-full aspect-video bg-white/5 rounded-xl border border-white/10 overflow-hidden p-4">
        <div className="grid grid-cols-4 grid-rows-3 gap-2 h-full">
          {heatmap.zones.map((zone, i) => {
            // Assign grid spanning to make it look like a store layout
            let spanClass = 'col-span-1 row-span-1';
            if (i === 0) spanClass = 'col-span-2 row-span-2';
            else if (i === 1) spanClass = 'col-span-2 row-span-1';
            else if (i === 2) spanClass = 'col-span-1 row-span-2';
            
            return (
              <div 
                key={zone.zone_id}
                className={`relative rounded-lg overflow-hidden group transition-all duration-500 ease-in-out ${spanClass}`}
                style={{ backgroundColor: getHeatColor(zone.normalized_score) }}
              >
                <div className="absolute inset-0 flex flex-col items-center justify-center p-2 text-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/60 backdrop-blur-sm z-10">
                  <span className="font-bold text-white mb-1">{zone.zone_id}</span>
                  <span className="text-xs text-gray-300">Visits: {zone.frequency}</span>
                  <span className="text-xs text-gray-300">Dwell: {(zone.avg_dwell_ms / 1000).toFixed(1)}s</span>
                </div>
                <div className="absolute inset-x-0 bottom-0 p-2 pointer-events-none">
                  <span className="text-xs font-semibold text-white/80 drop-shadow-md">{zone.zone_id}</span>
                </div>
              </div>
            );
          })}
          
          {/* Fill empty spots if less than enough zones */}
          {heatmap.zones.length < 5 && Array.from({length: 5 - heatmap.zones.length}).map((_, i) => (
             <div key={`empty-${i}`} className="bg-white/5 rounded-lg border border-dashed border-white/20"></div>
          ))}
        </div>
      </div>
      
      <div className="flex items-center justify-between mt-4 px-2">
        <span className="text-xs text-brand-muted">Low Traffic</span>
        <div className="flex-1 mx-4 h-2 rounded-full bg-gradient-to-r from-blue-500 via-yellow-500 to-red-500 opacity-80"></div>
        <span className="text-xs text-brand-muted">High Traffic</span>
      </div>
    </div>
  );
};

export default HeatmapView;
