import React, { useState } from 'react';
import { Compass, BarChart3, Network } from 'lucide-react';
import { GraphExplorer } from './components/GraphExplorer';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<'explorer' | 'analytics'>('explorer');
  const [selectedPackage, setSelectedPackage] = useState<string>('express');
  const [backend, setBackend] = useState<'igraph' | 'networkx'>('igraph');

  const handleNavigateToPackage = (pkg: string) => {
    setSelectedPackage(pkg);
    setActiveView('explorer');
  };

  return (
    <div className="app-container">
      {/* Top Main Navigation Bar */}
      <header className="navbar">
        <div className="brand" onClick={() => setActiveView('explorer')}>
          <div className="brand-icon">
            <Network size={20} color="#ffffff" />
          </div>
          <div>
            <span className="brand-title">SupplyChainLens</span>
            <span className="brand-badge" style={{ marginLeft: 8 }}>
              v0.1.0
            </span>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeView === 'explorer' ? 'active' : ''}`}
            onClick={() => setActiveView('explorer')}
          >
            <Compass size={16} />
            Graph Explorer
          </button>
          <button
            className={`nav-tab-btn ${activeView === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveView('analytics')}
          >
            <BarChart3 size={16} />
            Analytics Dashboard
          </button>
        </div>

        {/* Actions & Backend Switcher */}
        <div className="nav-actions">
          <div className="backend-badge">
            <div className="backend-dot" />
            <span>Engine:</span>
            <select
              value={backend}
              onChange={(e) => setBackend(e.target.value as 'igraph' | 'networkx')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#f8fafc',
                fontWeight: 600,
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="igraph" style={{ background: '#0f1422' }}>
                igraph (C-Core)
              </option>
              <option value="networkx" style={{ background: '#0f1422' }}>
                NetworkX
              </option>
            </select>
          </div>
        </div>
      </header>

      {/* Main Active View */}
      <main className="main-view">
        {activeView === 'explorer' ? (
          <GraphExplorer
            initialPackage={selectedPackage}
            backend={backend}
            onSelectPackageForAnalytics={(pkg) => {
              setSelectedPackage(pkg);
              setActiveView('analytics');
            }}
          />
        ) : (
          <AnalyticsDashboard
            backend={backend}
            onExplorePackage={handleNavigateToPackage}
          />
        )}
      </main>
    </div>
  );
};

export default App;
