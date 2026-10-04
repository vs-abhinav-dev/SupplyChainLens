import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core, EventObject } from 'cytoscape';
import {
  Search,
  Maximize2,
  RotateCcw,
  Layers,
  ArrowDownRight,
  ArrowUpLeft,
  X,
  Compass,
} from 'lucide-react';
import { fetchPackages, fetchPackageSummary, fetchSubgraph } from '../api';
import type { GraphNode, PackageSummary, SubgraphResponse } from '../api';

interface GraphExplorerProps {
  initialPackage?: string;
  backend: string;
  onSelectPackageForAnalytics?: (pkg: string) => void;
}

export const GraphExplorer: React.FC<GraphExplorerProps> = ({
  initialPackage = 'express',
  backend,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [currentPackage, setCurrentPackage] = useState<string>(initialPackage);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const [depth, setDepth] = useState<number>(1);
  const [direction, setDirection] = useState<'both' | 'dependencies' | 'dependents'>('dependencies');
  const [layoutName, setLayoutName] = useState<string>('cose');
  const [loading, setLoading] = useState<boolean>(false);

  const [subgraphData, setSubgraphData] = useState<SubgraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [packageSummary, setPackageSummary] = useState<PackageSummary | null>(null);

  // Search autocomplete
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const pkgs = await fetchPackages(searchQuery, 8);
        setSearchResults(pkgs);
      } catch (err) {
        console.error(err);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load graph data
  const loadGraph = async (pkgName: string, d: number = depth, dir: string = direction) => {
    setLoading(true);
    try {
      const data = await fetchSubgraph(pkgName, d, dir, 150, backend);
      setSubgraphData(data);
      setCurrentPackage(pkgName);

      // Fetch package summary for inspector
      try {
        const cleanName = pkgName.replace('npm:', '').split('@')[0];
        const summary = await fetchPackageSummary(cleanName);
        setPackageSummary(summary);
      } catch (e) {
        setPackageSummary(null);
      }

      renderCytoscape(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph(currentPackage, depth, direction);
  }, [backend]);

  const renderCytoscape = (data: SubgraphResponse) => {
    if (!containerRef.current) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [];

    data.nodes.forEach((n) => {
      elements.push({
        group: 'nodes',
        data: {
          id: n.id,
          label: n.name,
          version: n.version,
          isRoot: n.is_root,
          degree: n.degree,
          inDegree: n.in_degree,
          outDegree: n.out_degree,
          packageId: n.package_id,
        },
      });
    });

    data.edges.forEach((e) => {
      elements.push({
        group: 'edges',
        data: {
          id: `${e.source}->${e.target}`,
          source: e.source,
          target: e.target,
          constraint: e.version_constraint,
          depType: e.dependency_type,
        },
      });
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#131929',
            'border-width': 2,
            'border-color': '#3b82f6',
            color: '#f8fafc',
            label: 'data(label)',
            'font-family': 'Inter, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 32,
            height: 32,
            'text-outline-color': '#0a0d14',
            'text-outline-width': 2,
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': 0.2,
          },
        },
        {
          selector: 'node[?isRoot]',
          style: {
            'background-color': '#06b6d4',
            'border-color': '#ffffff',
            'border-width': 3,
            width: 44,
            height: 44,
            'font-size': '13px',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'background-color': '#ec4899',
            'border-color': '#ffffff',
            'border-width': 3,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': 'rgba(148, 163, 184, 0.3)',
            'target-arrow-color': 'rgba(148, 163, 184, 0.6)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            label: 'data(constraint)',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            color: 'rgba(148, 163, 184, 0.7)',
            'text-outline-color': '#0a0d14',
            'text-outline-width': 1.5,
          },
        },
        {
          selector: 'edge:selected',
          style: {
            width: 2.5,
            'line-color': '#ec4899',
            'target-arrow-color': '#ec4899',
            color: '#ec4899',
          },
        },
      ],
      layout: getLayoutOptions(layoutName),
    });

    // Event listeners
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const nid = node.id();
      const nodeObj = data.nodes.find((item) => item.id === nid);
      if (nodeObj) {
        setSelectedNode(nodeObj);
      }
    });

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    // Set default selected node to root
    const rootNode = data.nodes.find((n) => n.is_root);
    if (rootNode) setSelectedNode(rootNode);
  };

  const getLayoutOptions = (name: string): cytoscape.LayoutOptions => {
    if (name === 'breadthfirst') {
      return { name: 'breadthfirst', directed: true, padding: 40, spacingFactor: 1.4 };
    } else if (name === 'concentric') {
      return { name: 'concentric', padding: 40, minNodeSpacing: 50 };
    } else if (name === 'circle') {
      return { name: 'circle', padding: 40 };
    }
    return {
      name: 'cose',
      animate: false,
      padding: 50,
      nodeRepulsion: () => 6000,
      idealEdgeLength: () => 80,
    };
  };

  const handleApplyLayout = (name: string) => {
    setLayoutName(name);
    if (cyRef.current) {
      const layout = cyRef.current.layout(getLayoutOptions(name));
      layout.run();
    }
  };

  const handleExpandNode = async (nodeId: string) => {
    if (!cyRef.current) return;
    setLoading(true);
    try {
      const newSubgraph = await fetchSubgraph(nodeId, 1, direction, 100, backend);
      const cy = cyRef.current;

      newSubgraph.nodes.forEach((n) => {
        if (cy.getElementById(n.id).length === 0) {
          cy.add({
            group: 'nodes',
            data: {
              id: n.id,
              label: n.name,
              version: n.version,
              isRoot: false,
              degree: n.degree,
              inDegree: n.in_degree,
              outDegree: n.out_degree,
              packageId: n.package_id,
            },
          });
        }
      });

      newSubgraph.edges.forEach((e) => {
        const edgeId = `${e.source}->${e.target}`;
        if (cy.getElementById(edgeId).length === 0) {
          cy.add({
            group: 'edges',
            data: {
              id: edgeId,
              source: e.source,
              target: e.target,
              constraint: e.version_constraint,
              depType: e.dependency_type,
            },
          });
        }
      });

      const layout = cy.layout(getLayoutOptions(layoutName));
      layout.run();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="explorer-container">
      {/* Central Interactive Graph Canvas */}
      <div className="canvas-area">
        {/* Floating Top Controls */}
        <div className="floating-controls">
          {/* Search Control */}
          <div className="control-pill">
            <div className="search-input-wrapper">
              <Search size={16} className="search-icon-pos" />
              <input
                type="text"
                className="search-input"
                placeholder="Search package (e.g. express, react)..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSearching(true);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    loadGraph(searchQuery.trim());
                    setIsSearching(false);
                  }
                }}
              />
              {isSearching && searchResults.length > 0 && (
                <div className="search-dropdown">
                  {searchResults.map((pkg) => (
                    <div
                      key={pkg}
                      className="search-item"
                      onClick={() => {
                        setSearchQuery(pkg);
                        setIsSearching(false);
                        loadGraph(pkg);
                      }}
                    >
                      <span>{pkg}</span>
                      <ArrowDownRight size={14} color="#64748b" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Traversal Controls */}
          <div className="control-pill">
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>DEPTH:</span>
            <div className="control-btn-group">
              {[1, 2, 3].map((d) => (
                <button
                  key={d}
                  className={`group-btn ${depth === d ? 'active' : ''}`}
                  onClick={() => {
                    setDepth(d);
                    loadGraph(currentPackage, d, direction);
                  }}
                >
                  {d}
                </button>
              ))}
            </div>

            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, marginLeft: 8 }}>
              DIRECTION:
            </span>
            <div className="control-btn-group">
              <button
                className={`group-btn ${direction === 'dependencies' ? 'active' : ''}`}
                title="Outgoing dependency tree"
                onClick={() => {
                  setDirection('dependencies');
                  loadGraph(currentPackage, depth, 'dependencies');
                }}
              >
                Dependencies
              </button>
              <button
                className={`group-btn ${direction === 'dependents' ? 'active' : ''}`}
                title="Incoming dependent tree (blast radius)"
                onClick={() => {
                  setDirection('dependents');
                  loadGraph(currentPackage, depth, 'dependents');
                }}
              >
                Dependents
              </button>
              <button
                className={`group-btn ${direction === 'both' ? 'active' : ''}`}
                onClick={() => {
                  setDirection('both');
                  loadGraph(currentPackage, depth, 'both');
                }}
              >
                Both
              </button>
            </div>
          </div>

          {/* Layout & Reset Buttons */}
          <div className="control-pill">
            <div className="control-btn-group">
              <button
                className={`group-btn ${layoutName === 'cose' ? 'active' : ''}`}
                onClick={() => handleApplyLayout('cose')}
              >
                Force
              </button>
              <button
                className={`group-btn ${layoutName === 'breadthfirst' ? 'active' : ''}`}
                onClick={() => handleApplyLayout('breadthfirst')}
              >
                Hierarchy
              </button>
              <button
                className={`group-btn ${layoutName === 'concentric' ? 'active' : ''}`}
                onClick={() => handleApplyLayout('concentric')}
              >
                Radial
              </button>
            </div>

            <button
              className="icon-btn"
              title="Fit to view"
              onClick={() => cyRef.current?.fit(undefined, 40)}
            >
              <Maximize2 size={16} />
            </button>
            <button
              className="icon-btn"
              title="Reset view"
              onClick={() => cyRef.current?.reset()}
            >
              <RotateCcw size={16} />
            </button>
          </div>
        </div>

        {/* Cytoscape Container */}
        <div id="cy-container" ref={containerRef} />

        {/* Loading Spinner */}
        {loading && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 10,
            }}
          >
            <div className="loading-spinner" />
          </div>
        )}

        {/* Truncated notice if graph reached max nodes */}
        {subgraphData?.truncated && (
          <div
            style={{
              position: 'absolute',
              bottom: 16,
              left: 16,
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              color: '#f59e0b',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.75rem',
              fontWeight: 500,
              zIndex: 20,
            }}
          >
            Subgraph capped at 150 nodes to preserve performance. Click nodes to expand localized branches.
          </div>
        )}
      </div>

      {/* Right Detail Inspector Drawer */}
      <div className="sidebar-drawer">
        {selectedNode ? (
          <>
            <div className="drawer-header">
              <div>
                <div className="drawer-title">{selectedNode.label}</div>
                <div className="drawer-subtitle">
                  Package: <span style={{ color: '#06b6d4' }}>{selectedNode.package_id}</span>
                </div>
              </div>
              <button className="icon-btn" onClick={() => setSelectedNode(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="drawer-content">
              {/* Quick Actions */}
              <button
                className="action-btn-primary"
                onClick={() => handleExpandNode(selectedNode.id)}
              >
                <Compass size={16} />
                Expand Node Neighborhood
              </button>

              <button
                className="action-btn-secondary"
                onClick={() => loadGraph(selectedNode.name, depth, 'dependencies')}
              >
                <ArrowDownRight size={16} />
                Focus Dependencies
              </button>

              <button
                className="action-btn-secondary"
                onClick={() => loadGraph(selectedNode.name, depth, 'dependents')}
              >
                <ArrowUpLeft size={16} />
                Focus Dependents (Blast Radius)
              </button>

              {/* Degrees Stats */}
              <div>
                <div className="list-section-title">Connectivity & Topology</div>
                <div className="stat-grid-2">
                  <div className="stat-card-mini">
                    <div className="label">In-Degree (Dependents)</div>
                    <div className="value" style={{ color: '#10b981' }}>
                      {selectedNode.in_degree}
                    </div>
                  </div>
                  <div className="stat-card-mini">
                    <div className="label">Out-Degree (Dependencies)</div>
                    <div className="value" style={{ color: '#3b82f6' }}>
                      {selectedNode.out_degree}
                    </div>
                  </div>
                </div>
              </div>

              {/* Package Summary & History */}
              {packageSummary && (
                <div>
                  <div className="list-section-title">Package Releases</div>
                  <div className="stat-card-mini" style={{ marginBottom: 10 }}>
                    <div className="label">Total Releases Recorded</div>
                    <div className="value">{packageSummary.total_versions}</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: 4 }}>
                      Latest: {packageSummary.latest_version}
                    </div>
                  </div>

                  <div className="chip-list">
                    {packageSummary.versions.slice(0, 20).map((ver) => (
                      <span
                        key={ver}
                        className={`chip ${ver === selectedNode.version ? 'active' : ''}`}
                        onClick={() => loadGraph(`${packageSummary.name}@${ver}`)}
                      >
                        v{ver}
                      </span>
                    ))}
                    {packageSummary.versions.length > 20 && (
                      <span className="chip" style={{ opacity: 0.6 }}>
                        +{packageSummary.versions.length - 20} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <Layers size={36} />
            <p>Select any node in the graph to inspect versions, dependencies, and blast radius.</p>
          </div>
        )}
      </div>
    </div>
  );
};
