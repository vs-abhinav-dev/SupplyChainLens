export interface GraphNode {
  id: string;
  label: string;
  name: string;
  version: string;
  package_id: string;
  published_at?: string;
  is_root: boolean;
  degree: number;
  in_degree: number;
  out_degree: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  version_constraint: string;
  dependency_type: string;
}

export interface SubgraphResponse {
  root_id: string;
  depth: number;
  direction: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  truncated: boolean;
}

export interface PackageSummary {
  package_id: string;
  name: string;
  ecosystem: string;
  total_versions: number;
  latest_version?: string;
  latest_node_id?: string;
  versions: string[];
  node_ids: string[];
}

export interface GraphStats {
  backend: string;
  node_count: number;
  edge_count: number;
  boundary_edge_count: number;
  package_count: number;
}

export interface PathResponse {
  source: string;
  target: string;
  found: boolean;
  length: number;
  path: string[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RankingItem {
  node_id: string;
  name: string;
  version: string;
  score: number;
  rank: number;
}

export interface RankingResult {
  metric: string;
  total_nodes: number;
  rankings: RankingItem[];
  summary: Record<string, number>;
}

export interface ComponentItem {
  component_id: number;
  size: number;
  sample_nodes: string[];
}

export interface ComponentsResult {
  component_type: string;
  total_components: number;
  max_component_size: number;
  components: ComponentItem[];
  size_distribution: Record<string, number>;
}

export interface CycleItem {
  cycle_id: number;
  length: number;
  cycle: string[];
}

export interface CyclesResult {
  total_cycles: number;
  has_cycles: boolean;
  cycles: CycleItem[];
}

export interface DependencyDepthResult {
  max_depth: number;
  avg_depth: number;
  depth_distribution: Record<string, number>;
  deepest_nodes: RankingItem[];
}

export interface DegreeAnalysisResult {
  total_nodes: number;
  total_edges: number;
  density: number;
  avg_degree: number;
  in_degree_distribution: Record<string, number>;
  out_degree_distribution: Record<string, number>;
  top_fan_in: RankingItem[];
  top_fan_out: RankingItem[];
}

const API_BASE = '/api';

export async function fetchGraphStats(backend?: string): Promise<GraphStats> {
  const url = backend ? `${API_BASE}/graph?backend=${backend}` : `${API_BASE}/graph`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch graph stats: ${res.statusText}`);
  return res.json();
}

export async function fetchPackages(query?: string, limit: number = 100): Promise<string[]> {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  params.set('limit', String(limit));
  const res = await fetch(`${API_BASE}/packages?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to list packages: ${res.statusText}`);
  const data = await res.json();
  return data.packages;
}

export async function fetchPackageSummary(pkgName: string): Promise<PackageSummary> {
  const clean = pkgName.replace('npm:', '');
  const res = await fetch(`${API_BASE}/packages/${encodeURIComponent(clean)}`);
  if (!res.ok) throw new Error(`Package '${pkgName}' not found`);
  return res.json();
}

export async function fetchSubgraph(
  identifier: string,
  depth: number = 1,
  direction: string = 'both',
  maxNodes: number = 150,
  backend?: string
): Promise<SubgraphResponse> {
  const params = new URLSearchParams({
    depth: String(depth),
    direction,
    max_nodes: String(maxNodes),
  });
  if (backend) params.set('backend', backend);
  const clean = identifier.replace('npm:', '');
  const res = await fetch(`${API_BASE}/graph/${encodeURIComponent(clean)}?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch subgraph for ${identifier}: ${res.statusText}`);
  return res.json();
}

export async function fetchShortestPath(source: string, target: string, backend?: string): Promise<PathResponse> {
  const params = new URLSearchParams({ source, target });
  if (backend) params.set('backend', backend);
  const res = await fetch(`${API_BASE}/graph/path?${params.toString()}`);
  if (!res.ok) throw new Error(`Path finding query failed: ${res.statusText}`);
  return res.json();
}

export async function fetchAnalytics<T = any>(
  algorithm: string,
  params: Record<string, string | number | boolean> = {}
): Promise<T> {
  const searchParams = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    searchParams.set(k, String(v));
  }
  const res = await fetch(`${API_BASE}/analytics/${algorithm}?${searchParams.toString()}`);
  if (!res.ok) throw new Error(`Analytics algorithm '${algorithm}' failed: ${res.statusText}`);
  return res.json();
}
