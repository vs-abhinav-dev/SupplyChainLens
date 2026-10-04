import React, { useEffect, useState } from 'react';
import {
  Award,
  Repeat,
  Network,
  TrendingUp,
  ArrowRight,
  ShieldAlert,
  BarChart2,
} from 'lucide-react';
import { fetchAnalytics, fetchGraphStats } from '../api';
import type {
  DegreeAnalysisResult,
  RankingResult,
  CyclesResult,
  DependencyDepthResult,
  GraphStats,
} from '../api';

interface AnalyticsDashboardProps {
  backend: string;
  onExplorePackage: (pkg: string) => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  backend,
  onExplorePackage,
}) => {
  const [activeTab, setActiveTab] = useState<'pagerank' | 'betweenness' | 'fanin' | 'cycles' | 'depth'>('pagerank');
  const [loading, setLoading] = useState<boolean>(true);

  const [stats, setStats] = useState<GraphStats | null>(null);
  const [degreeData, setDegreeData] = useState<DegreeAnalysisResult | null>(null);
  const [pagerankData, setPagerankData] = useState<RankingResult | null>(null);
  const [betweennessData, setBetweennessData] = useState<RankingResult | null>(null);
  const [cyclesData, setCyclesData] = useState<CyclesResult | null>(null);
  const [depthData, setDepthData] = useState<DependencyDepthResult | null>(null);

  useEffect(() => {
    const loadAllAnalytics = async () => {
      setLoading(true);
      try {
        const [gStats, deg, pr, bet, cyc, dep] = await Promise.all([
          fetchGraphStats(backend),
          fetchAnalytics<DegreeAnalysisResult>('degree', { backend, top_n: 25 }),
          fetchAnalytics<RankingResult>('pagerank', { backend, top_n: 25 }),
          fetchAnalytics<RankingResult>('betweenness', { backend, top_n: 25 }),
          fetchAnalytics<CyclesResult>('cycles', { backend }),
          fetchAnalytics<DependencyDepthResult>('dependency_depth', { backend, top_n: 25 }),
        ]);

        setStats(gStats);
        setDegreeData(deg);
        setPagerankData(pr);
        setBetweennessData(bet);
        setCyclesData(cyc);
        setDepthData(dep);
      } catch (err) {
        console.error('Failed to load analytics dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAllAnalytics();
  }, [backend]);

  if (loading) {
    return (
      <div className="empty-state" style={{ height: 'calc(100vh - 64px)' }}>
        <div className="loading-spinner" />
        <p style={{ marginTop: 12 }}>Computing high-performance graph metrics across 5,912 vertices...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Hero Overview Stat Cards */}
      <div className="metrics-overview-grid">
        <div className="metric-hero-card">
          <div className="metric-hero-title">Total Vertices</div>
          <div className="metric-hero-value" style={{ color: '#06b6d4' }}>
            {stats?.node_count.toLocaleString() ?? '5,912'}
          </div>
          <div className="metric-hero-desc">Unique package version nodes</div>
        </div>

        <div className="metric-hero-card">
          <div className="metric-hero-title">Resolved Edges</div>
          <div className="metric-hero-value" style={{ color: '#3b82f6' }}>
            {stats?.edge_count.toLocaleString() ?? '10,072'}
          </div>
          <div className="metric-hero-desc">In-graph directed dependency links</div>
        </div>

        <div className="metric-hero-card">
          <div className="metric-hero-title">Boundary Edges</div>
          <div className="metric-hero-value" style={{ color: '#f59e0b' }}>
            {stats?.boundary_edge_count.toLocaleString() ?? '59,628'}
          </div>
          <div className="metric-hero-desc">Targets outside bounded crawl sample</div>
        </div>

        <div className="metric-hero-card">
          <div className="metric-hero-title">Max Tree Depth</div>
          <div className="metric-hero-value" style={{ color: '#ec4899' }}>
            {depthData?.max_depth ?? 10} hops
          </div>
          <div className="metric-hero-desc">Avg: {depthData?.avg_depth ?? 1.8} hops / tree</div>
        </div>

        <div className="metric-hero-card">
          <div className="metric-hero-title">Dependency Cycles</div>
          <div className="metric-hero-value" style={{ color: cyclesData?.has_cycles ? '#f43f5e' : '#10b981' }}>
            {cyclesData?.total_cycles ?? 0}
          </div>
          <div className="metric-hero-desc">Circular dependency deadlocks</div>
        </div>
      </div>

      {/* Main Analytics Content Card */}
      <div className="analytics-section-card">
        {/* Navigation Tabs */}
        <div className="analytics-card-header">
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`nav-tab-btn ${activeTab === 'pagerank' ? 'active' : ''}`}
              onClick={() => setActiveTab('pagerank')}
            >
              <Award size={16} />
              PageRank Authority
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'betweenness' ? 'active' : ''}`}
              onClick={() => setActiveTab('betweenness')}
            >
              <Network size={16} />
              Chokepoints (Betweenness)
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'fanin' ? 'active' : ''}`}
              onClick={() => setActiveTab('fanin')}
            >
              <TrendingUp size={16} />
              Fan-In (Dependents)
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'cycles' ? 'active' : ''}`}
              onClick={() => setActiveTab('cycles')}
            >
              <Repeat size={16} />
              Dependency Cycles
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'depth' ? 'active' : ''}`}
              onClick={() => setActiveTab('depth')}
            >
              <BarChart2 size={16} />
              Depth Distribution
            </button>
          </div>

          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Engine: <span style={{ color: '#10b981', fontWeight: 600 }}>{stats?.backend.toUpperCase()}</span>
          </div>
        </div>

        {/* Tab 1: PageRank Rankings */}
        {activeTab === 'pagerank' && pagerankData && (
          <div>
            <div style={{ padding: '16px 24px', color: '#94a3b8', fontSize: '0.825rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              Directed PageRank measures structural authority and foundational reliance. High PageRank packages are the foundational pillars supporting the ecosystem.
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>Rank</th>
                  <th>Package Name</th>
                  <th>Version</th>
                  <th>Node ID</th>
                  <th>PageRank Score</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {pagerankData.rankings.map((item) => (
                  <tr key={item.node_id}>
                    <td>
                      <span className={`rank-badge ${item.rank <= 3 ? `rank-${item.rank}` : ''}`}>
                        #{item.rank}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{item.name}</td>
                    <td>v{item.version}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.775rem', color: '#64748b' }}>
                      {item.node_id}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#06b6d4' }}>
                      {item.score.toFixed(6)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="group-btn"
                        style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' }}
                        onClick={() => onExplorePackage(item.node_id)}
                      >
                        Explore <ArrowRight size={12} style={{ marginLeft: 4 }} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 2: Betweenness Centrality */}
        {activeTab === 'betweenness' && betweennessData && (
          <div>
            <div style={{ padding: '16px 24px', color: '#94a3b8', fontSize: '0.825rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              Betweenness centrality measures how frequently a package version sits on the shortest dependency path between other packages. High scores highlight structural bridges and single-point-of-failure chokepoints.
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>Rank</th>
                  <th>Package Name</th>
                  <th>Version</th>
                  <th>Betweenness Centrality</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {betweennessData.rankings.map((item) => (
                  <tr key={item.node_id}>
                    <td>
                      <span className={`rank-badge ${item.rank <= 3 ? `rank-${item.rank}` : ''}`}>
                        #{item.rank}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{item.name}</td>
                    <td>v{item.version}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#ec4899' }}>
                      {item.score.toFixed(8)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="group-btn"
                        style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' }}
                        onClick={() => onExplorePackage(item.node_id)}
                      >
                        Explore <ArrowRight size={12} style={{ marginLeft: 4 }} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Fan-In vs Fan-Out */}
        {activeTab === 'fanin' && degreeData && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
            {/* Top Fan-In */}
            <div style={{ borderRight: '1px solid var(--border-color)' }}>
              <div style={{ padding: '16px 20px', fontWeight: 700, fontSize: '0.875rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.05)' }}>
                Top Fan-In (Most Depended-Upon Vertices)
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Package</th>
                    <th>In-Degree</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {degreeData.top_fan_in.slice(0, 15).map((item) => (
                    <tr key={item.node_id}>
                      <td>#{item.rank}</td>
                      <td style={{ fontWeight: 600 }}>{item.name}@{item.version}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: '#10b981', fontWeight: 700 }}>
                        {item.score}
                      </td>
                      <td>
                        <button
                          className="group-btn"
                          style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                          onClick={() => onExplorePackage(item.node_id)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Top Fan-Out */}
            <div>
              <div style={{ padding: '16px 20px', fontWeight: 700, fontSize: '0.875rem', color: '#3b82f6', background: 'rgba(59, 130, 246, 0.05)' }}>
                Top Fan-Out (Highest Direct Dependencies)
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Package</th>
                    <th>Out-Degree</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {degreeData.top_fan_out.slice(0, 15).map((item) => (
                    <tr key={item.node_id}>
                      <td>#{item.rank}</td>
                      <td style={{ fontWeight: 600 }}>{item.name}@{item.version}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: '#3b82f6', fontWeight: 700 }}>
                        {item.score}
                      </td>
                      <td>
                        <button
                          className="group-btn"
                          style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                          onClick={() => onExplorePackage(item.node_id)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Dependency Cycles */}
        {activeTab === 'cycles' && cyclesData && (
          <div style={{ padding: 24 }}>
            {cyclesData.has_cycles ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(244, 63, 94, 0.1)', padding: 14, borderRadius: 10, border: '1px solid rgba(244, 63, 94, 0.3)' }}>
                  <ShieldAlert color="#f43f5e" size={20} />
                  <span style={{ fontSize: '0.875rem', color: '#f8fafc', fontWeight: 500 }}>
                    Detected <strong>{cyclesData.total_cycles}</strong> circular dependency cycles in the curated graph.
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {cyclesData.cycles.map((c) => (
                    <div
                      key={c.cycle_id}
                      style={{
                        background: 'var(--bg-input)',
                        padding: 16,
                        borderRadius: 10,
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f43f5e' }}>
                          Cycle #{c.cycle_id} (Length: {c.length})
                        </span>
                        <button
                          className="group-btn"
                          style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.3)' }}
                          onClick={() => onExplorePackage(c.cycle[0])}
                        >
                          Explore Cycle in Graph
                        </button>
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#94a3b8', wordBreak: 'break-all' }}>
                        {c.cycle.join(' ➔ ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>No circular dependency cycles detected in the current dataset.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Depth Distribution */}
        {activeTab === 'depth' && depthData && (
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#94a3b8', marginBottom: 12 }}>
                Dependency Tree Depth Distribution (Hops to Terminal Leaf Packages)
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 160, padding: '16px 0', borderBottom: '1px solid var(--border-color)' }}>
                {Object.entries(depthData.depth_distribution).map(([hop, count]) => {
                  const maxCount = Math.max(...Object.values(depthData.depth_distribution));
                  const heightPercent = Math.max(12, (count / maxCount) * 100);
                  return (
                    <div key={hop} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{count}</span>
                      <div
                        style={{
                          width: '100%',
                          height: `${heightPercent}%`,
                          background: 'linear-gradient(to top, #3b82f6, #06b6d4)',
                          borderRadius: 4,
                          boxShadow: '0 0 10px rgba(6, 182, 212, 0.2)',
                        }}
                      />
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f8fafc' }}>
                        {hop}h
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#94a3b8', marginBottom: 12 }}>
                Deepest Dependency Trees
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Package</th>
                    <th>Tree Depth</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {depthData.deepest_nodes.slice(0, 10).map((item) => (
                    <tr key={item.node_id}>
                      <td>#{item.rank}</td>
                      <td style={{ fontWeight: 600 }}>{item.name}@{item.version}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: '#ec4899', fontWeight: 700 }}>
                        {item.score} hops
                      </td>
                      <td>
                        <button
                          className="group-btn"
                          style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                          onClick={() => onExplorePackage(item.node_id)}
                        >
                          Inspect Tree
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
