import React, { useState, useEffect } from 'react';
import { Store, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  storeId: string;
  setStoreId: (id: string) => void;
  isConnected: boolean;
}

const Header: React.FC<HeaderProps> = ({ storeId, setStoreId, isConnected }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="glass-panel sticky top-0 z-50 border-b border-white/10 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-primary to-brand-secondary flex items-center justify-center shadow-lg shadow-brand-primary/20">
          <Store className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-primary via-brand-secondary to-brand-text hidden sm:block">
          Store Intelligence
        </h1>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden md:block text-brand-muted font-medium font-mono text-sm">
          {time.toLocaleTimeString()}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            className="bg-brand-background/50 border border-white/10 rounded-lg px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-primary/50 text-brand-text appearance-none cursor-pointer"
          >
            <option value="ST1076">Store ST1076 - Main</option>
            <option value="store_1076">Store 1076 - Secondary</option>
            <option value="STORE_001">Store 001 - Downtown</option>
            <option value="STORE_002">Store 002 - Uptown</option>
          </select>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5">
          {isConnected ? (
            <>
              <div className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-success opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-success"></span>
              </div>
              <Wifi className="w-4 h-4 text-brand-success" />
              <span className="text-xs font-medium text-brand-success hidden sm:block">Live</span>
            </>
          ) : (
            <>
              <div className="relative flex h-3 w-3">
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-danger"></span>
              </div>
              <WifiOff className="w-4 h-4 text-brand-danger" />
              <span className="text-xs font-medium text-brand-danger hidden sm:block">Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
