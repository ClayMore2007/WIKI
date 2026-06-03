import chainsJson from "../data/cache/industry_chains.json";
import companiesJson from "../data/cache/companies.json";
import metaJson from "../data/cache/meta.json";
import sourcesJson from "../data/cache/sources.json";
import watchlistJson from "../data/cache/watchlist.json";
import type { Company, IndustryChain, Meta, SourceFile, WatchlistItem } from "./types";

export const chains = chainsJson as IndustryChain[];
export const companies = companiesJson as Company[];
export const watchlist = watchlistJson as WatchlistItem[];
export const sources = sourcesJson as SourceFile[];
export const meta = metaJson as Meta;
