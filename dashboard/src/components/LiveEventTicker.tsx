import React, { useRef, useEffect } from 'react';
import { LiveEvent } from '../types';
import { Radio } from 'lucide-react';

interface LiveEventTickerProps {
  events: LiveEvent[];
}

const getEventColor = (type: string) => {
  if (type.includes('ENTER')) return 'text-brand-success bg-brand-success/10 border-brand-success/20';
  if (type.includes('EXIT')) return 'text-brand-muted bg-white/5 border-white/10';
  if (type.includes('PURCHASE')) return 'text-brand-primary bg-brand-primary/10 border-brand-primary/20';
  if (type.includes('ZONE')) return 'text-brand-secondary bg-brand-secondary/10 border-brand-secondary/20';
  return 'text-white bg-white/10 border-white/20';
};

const formatTime = (isoString: string) => {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    return isoString;
  }
};

const LiveEventTicker: React.FC<LiveEventTickerProps> = ({ events }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to left when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = 0;
    }
  }, [events]);

  return (
    <div className="fixed bottom-0 left-0 right-0 h-12 glass-panel border-t border-white/10 flex items-center px-4 z-40 bg-brand-background/95">
      <div className="flex items-center gap-2 mr-4 shrink-0">
        <Radio className="w-4 h-4 text-brand-primary animate-pulse" />
        <span className="text-xs font-bold uppercase tracking-widest text-brand-primary">Live Feed</span>
      </div>
      
      <div className="w-px h-6 bg-white/10 mx-2 shrink-0"></div>
      
      <div 
        ref={scrollRef}
        className="flex-1 overflow-x-auto flex items-center gap-3 no-scrollbar scroll-smooth whitespace-nowrap mask-edges"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        <style>{`
          .mask-edges {
            mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
            -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
          }
        `}</style>
        
        {events.length === 0 ? (
          <span className="text-sm text-brand-muted italic">Waiting for events...</span>
        ) : (
          events.map((ev, i) => (
            <div 
              key={`${ev.timestamp}-${i}`}
              className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium shrink-0 animate-fade-in ${getEventColor(ev.event_type)}`}
            >
              <span className="opacity-60">{formatTime(ev.timestamp)}</span>
              <span>{ev.event_type}</span>
              {ev.visitor_id && <span className="opacity-80">| {ev.visitor_id.substring(0, 8)}</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LiveEventTicker;
