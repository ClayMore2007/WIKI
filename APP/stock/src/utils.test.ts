import { describe, expect, it } from "vitest";
import { formatChange, heatLevel, importanceRank, matchesMindmapSearch, matchesSearch, toggleSetValue } from "./utils";
import type { Company, MindmapNode } from "./types";

const company: Company = {
  name: "新易盛",
  code: "SZ300502",
  chainIds: ["光模块-cpo"],
  stageIds: ["光模块-cpo-光模块龙头"],
  chains: ["光模块/CPO"],
  stages: ["光模块龙头"],
  priority: "P0",
  heat: 7,
  price: "628.99",
  priceDate: "20260513",
  ownership: "自选",
  notes: ["自选池内光模块核心标的"],
  risks: [],
  sourceRefs: [],
  summary: "光模块核心标的",
  cardPath: ""
};

const mindmapNode: MindmapNode = {
  id: "idea",
  type: "text",
  text: "华能蒙电（K线底部）",
  x: 80,
  y: 20,
  width: 260,
  height: 90,
  color: "6",
  importance: "高",
  importanceRank: 1,
  kind: "company",
  companyNames: ["华能蒙电"],
  actionTags: ["K线底部"],
  parentNodeIds: ["power"],
  parentNodeTexts: ["电力"],
  childNodeIds: ["risk"],
  childNodeTexts: ["等待确认"]
};

describe("formatChange", () => {
  it("formats available local snapshot changes", () => {
    expect(formatChange({ status: "ok", fromDate: "20260526", percent: 10 })).toBe("+10.00% · 20260526");
  });

  it("reports insufficient local snapshots", () => {
    expect(formatChange({ status: "本地快照不足" })).toBe("本地快照不足");
  });
});

describe("matchesSearch", () => {
  it("matches company name, code, chain, stage and notes", () => {
    expect(matchesSearch(company, "新易盛")).toBe(true);
    expect(matchesSearch(company, "300502")).toBe(true);
    expect(matchesSearch(company, "CPO")).toBe(true);
    expect(matchesSearch(company, "核心标的")).toBe(true);
  });

  it("treats empty search as a match", () => {
    expect(matchesSearch(company, "")).toBe(true);
  });
});

describe("matchesMindmapSearch", () => {
  it("matches node text, company names and action tags", () => {
    expect(matchesMindmapSearch(mindmapNode, "华能")).toBe(true);
    expect(matchesMindmapSearch(mindmapNode, "K线")).toBe(true);
    expect(matchesMindmapSearch(mindmapNode, "电力")).toBe(true);
    expect(matchesMindmapSearch(mindmapNode, "等待确认")).toBe(true);
    expect(matchesMindmapSearch(mindmapNode, "算力")).toBe(false);
  });

  it("treats empty search as a match", () => {
    expect(matchesMindmapSearch(mindmapNode, "")).toBe(true);
  });
});

describe("importanceRank", () => {
  it("sorts mindmap importance labels from most to least important", () => {
    expect(["低", "最高", "未标色", "高", "中"].sort((a, b) => importanceRank(a) - importanceRank(b))).toEqual([
      "最高",
      "高",
      "中",
      "低",
      "未标色"
    ]);
  });
});

describe("toggleSetValue", () => {
  it("adds a missing value and removes an existing value", () => {
    expect(toggleSetValue(new Set(["topic"]), "company")).toEqual(new Set(["topic", "company"]));
    expect(toggleSetValue(new Set(["topic", "company"]), "company")).toEqual(new Set(["topic"]));
  });
});

describe("heatLevel", () => {
  it("maps heat into stable css levels", () => {
    expect(heatLevel(0, 20)).toBe(0);
    expect(heatLevel(5, 20)).toBe(2);
    expect(heatLevel(12, 20)).toBe(4);
    expect(heatLevel(20, 20)).toBe(5);
  });
});
