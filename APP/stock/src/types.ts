export interface SourceRef {
  target: string;
  label: string;
}

export interface ChainCompany {
  name: string;
  code: string;
  priority: string;
  heat: number;
}

export interface ChainStage {
  id: string;
  chainId: string;
  name: string;
  priority: string;
  companies: ChainCompany[];
}

export interface IndustryChain {
  id: string;
  name: string;
  bottleneckLevel: string;
  stages: ChainStage[];
  heatByMonth: Record<string, number>;
}

export interface Company {
  name: string;
  code: string;
  chainIds: string[];
  stageIds: string[];
  chains: string[];
  stages: string[];
  priority: string;
  heat: number;
  price: string;
  priceDate: string;
  ownership: string;
  notes: string[];
  risks: string[];
  sourceRefs: SourceRef[];
  summary: string;
  cardPath: string;
  dateRange?: string;
}

export interface SnapshotChange {
  status: "ok" | "本地快照不足";
  fromDate?: string;
  percent?: number;
}

export interface WatchlistItem {
  code: string;
  name: string;
  price: string;
  priceDate: string;
  market: string;
  ownership: string;
  note: string;
  chainIds: string[];
  chains: string[];
  priority: string;
  heat: number;
  change5d: SnapshotChange;
  change10d: SnapshotChange;
}

export interface SourceFile {
  title: string;
  month: string;
  path: string;
  companies: string[];
}

export interface MindmapNode {
  id: string;
  type: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  importance: "最高" | "高" | "中" | "低" | "未标色";
  importanceRank: number;
  kind: "topic" | "company" | "action" | "note";
  companyNames: string[];
  actionTags: string[];
  parentNodeIds: string[];
  parentNodeTexts: string[];
  childNodeIds: string[];
  childNodeTexts: string[];
}

export interface MindmapEdge {
  id: string;
  source: string;
  target: string;
}

export interface Mindmap {
  nodes: MindmapNode[];
  edges: MindmapEdge[];
}

export interface Meta {
  generatedAt: string;
  wikiRoot: string;
  disclaimer: string;
}
