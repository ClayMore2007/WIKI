import { describe, expect, it } from "vitest";
import { formatChange, heatLevel, matchesSearch } from "./utils";
import type { Company } from "./types";

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

describe("heatLevel", () => {
  it("maps heat into stable css levels", () => {
    expect(heatLevel(0, 20)).toBe(0);
    expect(heatLevel(5, 20)).toBe(2);
    expect(heatLevel(12, 20)).toBe(4);
    expect(heatLevel(20, 20)).toBe(5);
  });
});
