"use client";

import { useEffect, useState } from "react";

interface HealthData {
  status: string;
  services: {
    api: string;
    postgres: string;
    redis: string;
  };
}

export default function HealthStatus() {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${apiUrl}/health`);
      if (!response.ok) {
        throw new Error("Backend service returned degraded status");
      }
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to reach backend");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Poll every 10 seconds for real-time dashboard status
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (statusText: string) => {
    if (statusText === "online" || statusText === "healthy") {
      return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    }
    if (statusText === "degraded") {
      return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    }
    return "text-rose-400 bg-rose-500/10 border-rose-500/20";
  };

  const getStatusDot = (statusText: string) => {
    if (statusText === "online" || statusText === "healthy") {
      return "bg-emerald-400 shadow-emerald-400/50";
    }
    if (statusText === "degraded") {
      return "bg-amber-400 shadow-amber-400/50";
    }
    return "bg-rose-400 shadow-rose-400/50";
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl transition-all duration-300 hover:border-violet-500/30">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">System Status Panel</h3>
        <button 
          onClick={fetchHealth} 
          disabled={loading}
          className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-zinc-300 font-medium transition disabled:opacity-50"
        >
          {loading ? "Refreshing..." : "Check Now"}
        </button>
      </div>

      {loading && !data && (
        <div className="flex flex-col items-center justify-center py-6">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent mb-2"></div>
          <p className="text-sm text-zinc-400">Querying platform nodes...</p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-4 mb-4 text-sm text-rose-400">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
            <span className="font-semibold">Backend Degraded / Offline</span>
          </div>
          <p className="text-xs text-rose-300/80">
            Is docker-compose up running? Error: {error}
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-sm text-zinc-400">Core API Status</span>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold ${getStatusColor(data.services.api)}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${getStatusDot(data.services.api)} animate-pulse`}></span>
              {data.services.api.toUpperCase()}
            </div>
          </div>
          
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-sm text-zinc-400">PostgreSQL Engine</span>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold ${getStatusColor(data.services.postgres)}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${getStatusDot(data.services.postgres)}`}></span>
              {data.services.postgres.toUpperCase()}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">Redis Cache Cluster</span>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold ${getStatusColor(data.services.redis)}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${getStatusDot(data.services.redis)}`}></span>
              {data.services.redis.toUpperCase()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
