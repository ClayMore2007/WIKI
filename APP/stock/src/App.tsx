import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  ChevronRight,
  Database,
  FileText,
  RefreshCw,
  Search,
  Star,
  Table2
} from "lucide-react";
import { useMemo, useState } from "react";
import { chains, companies, meta, sources, watchlist } from "./data";
import type { Company, IndustryChain, WatchlistItem } from "./types";
import { formatChange, heatLevel, matchesSearch, matchesWatchlistSearch, priorityRank, unique } from "./utils";

type Page = "matrix" | "watchlist" | "notes";
type OwnershipFilter = "all" | "holding" | "watch";

const priorities = ["all", "P0", "P1", "P2", "P3"];

export function App() {
  const [page, setPage] = useState<Page>("matrix");
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("all");
  const [ownership, setOwnership] = useState<OwnershipFilter>("all");
  const [selectedCompanyName, setSelectedCompanyName] = useState(companies[0]?.name ?? "");

  const selectedCompany = companies.find((company) => company.name === selectedCompanyName) ?? companies[0];
  const filteredCompanies = useMemo(
    () =>
      companies.filter((company) => {
        const priorityMatch = priority === "all" || company.priority === priority;
        const ownershipMatch =
          ownership === "all" ||
          (ownership === "holding" && company.ownership.includes("持仓")) ||
          (ownership === "watch" && company.ownership.includes("自选"));
        return priorityMatch && ownershipMatch && matchesSearch(company, query);
      }),
    [ownership, priority, query]
  );

  return (
    <div className="appShell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ClayMore Stock Wiki</p>
          <h1>股票产业链雷达</h1>
        </div>
        <div className="topActions">
          <a className="ghostButton" href="#" title="运行 npm run build:cache 后刷新页面">
            <RefreshCw size={16} />
            更新缓存
          </a>
          <span className="timestamp">缓存：{meta.generatedAt}</span>
        </div>
      </header>

      <section className="riskBanner">
        <AlertTriangle size={18} />
        <span>{meta.disclaimer}</span>
      </section>

      <nav className="tabs" aria-label="页面">
        <button className={page === "matrix" ? "active" : ""} onClick={() => setPage("matrix")}>
          <BarChart3 size={17} />
          产业链热力矩阵
        </button>
        <button className={page === "watchlist" ? "active" : ""} onClick={() => setPage("watchlist")}>
          <Table2 size={17} />
          自选/持仓
        </button>
        <button className={page === "notes" ? "active" : ""} onClick={() => setPage("notes")}>
          <FileText size={17} />
          笔记
        </button>
      </nav>

      <FilterBar
        query={query}
        setQuery={setQuery}
        priority={priority}
        setPriority={setPriority}
        ownership={ownership}
        setOwnership={setOwnership}
      />

      {page === "matrix" ? (
        <MatrixPage
          selectedCompany={selectedCompany}
          filteredCompanies={filteredCompanies}
          onSelectCompany={setSelectedCompanyName}
        />
      ) : page === "watchlist" ? (
        <WatchlistPage query={query} priority={priority} ownership={ownership} onSelectCompany={setSelectedCompanyName} />
      ) : (
        <NotesPage companies={filteredCompanies} onSelectCompany={setSelectedCompanyName} />
      )}
    </div>
  );
}

function FilterBar({
  query,
  setQuery,
  priority,
  setPriority,
  ownership,
  setOwnership
}: {
  query: string;
  setQuery: (value: string) => void;
  priority: string;
  setPriority: (value: string) => void;
  ownership: OwnershipFilter;
  setOwnership: (value: OwnershipFilter) => void;
}) {
  return (
    <section className="filters">
      <label className="searchBox">
        <Search size={16} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索公司、代码、产业链、备注" />
      </label>
      <div className="segmented">
        {priorities.map((item) => (
          <button key={item} className={priority === item ? "active" : ""} onClick={() => setPriority(item)}>
            {item === "all" ? "全部P级" : item}
          </button>
        ))}
      </div>
      <div className="segmented">
        <button className={ownership === "all" ? "active" : ""} onClick={() => setOwnership("all")}>
          全部
        </button>
        <button className={ownership === "holding" ? "active" : ""} onClick={() => setOwnership("holding")}>
          持仓
        </button>
        <button className={ownership === "watch" ? "active" : ""} onClick={() => setOwnership("watch")}>
          自选
        </button>
      </div>
    </section>
  );
}

function MatrixPage({
  selectedCompany,
  filteredCompanies,
  onSelectCompany
}: {
  selectedCompany: Company;
  filteredCompanies: Company[];
  onSelectCompany: (name: string) => void;
}) {
  const months = useMemo(() => unique(sources.map((source) => source.month)).filter((month) => month !== "日期未知").sort(), []);
  const maxHeat = Math.max(1, ...chains.flatMap((chain) => Object.values(chain.heatByMonth)));
  const companyNames = new Set(filteredCompanies.map((company) => company.name));
  const visibleChains = chains
    .map((chain) => ({
      ...chain,
      stages: chain.stages
        .map((stage) => ({ ...stage, companies: stage.companies.filter((company) => companyNames.has(company.name)) }))
        .filter((stage) => stage.companies.length > 0)
    }))
    .filter((chain) => chain.stages.length > 0);

  return (
    <main className="matrixLayout">
      <aside className="chainPanel">
        <PanelTitle icon={<Database size={17} />} title="产业链结构" meta={`${visibleChains.length} 条主线`} />
        <div className="chainTree">
          {visibleChains.map((chain) => (
            <ChainNode key={chain.id} chain={chain} onSelectCompany={onSelectCompany} selectedCompany={selectedCompany.name} />
          ))}
        </div>
      </aside>

      <section className="heatPanel">
        <PanelTitle icon={<BarChart3 size={17} />} title="时间轴资料热力" meta="按资料月份聚合" />
        <div className="heatGrid" style={{ gridTemplateColumns: `220px repeat(${months.length}, minmax(64px, 1fr))` }}>
          <div className="gridHeader stickyCol">主线 / 环节</div>
          {months.map((month) => (
            <div className="gridHeader" key={month}>
              {month}
            </div>
          ))}
          {visibleChains.map((chain) => (
            <HeatRow key={chain.id} label={chain.name} heatByMonth={chain.heatByMonth} months={months} maxHeat={maxHeat} />
          ))}
        </div>
        <section className="sourceStrip">
          <h2>近期资料入口</h2>
          <div className="sourceList">
            {sources.slice(0, 16).map((source) => (
              <div className="sourceItem" key={source.path}>
                <FileText size={14} />
                <span>{source.title}</span>
                <b>{source.month}</b>
              </div>
            ))}
          </div>
        </section>
      </section>

      <CompanyDetail company={selectedCompany} />
    </main>
  );
}

function ChainNode({
  chain,
  selectedCompany,
  onSelectCompany
}: {
  chain: IndustryChain;
  selectedCompany: string;
  onSelectCompany: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="chainNode">
      <button className="treeButton chainButton" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        <span>{chain.name}</span>
      </button>
      {open && (
        <div className="stageList">
          {chain.stages.map((stage) => (
            <details key={stage.id} open>
              <summary>
                <span>{stage.name}</span>
                <b>{stage.priority}</b>
              </summary>
              <div className="companyList">
                {stage.companies
                  .slice()
                  .sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority) || b.heat - a.heat)
                  .map((company) => (
                    <button
                      key={`${stage.id}-${company.code}-${company.name}`}
                      className={selectedCompany === company.name ? "companyButton active" : "companyButton"}
                      onClick={() => onSelectCompany(company.name)}
                    >
                      <span>{company.name}</span>
                      <small>{company.priority} · 热{company.heat}</small>
                    </button>
                  ))}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}

function HeatRow({
  label,
  heatByMonth,
  months,
  maxHeat
}: {
  label: string;
  heatByMonth: Record<string, number>;
  months: string[];
  maxHeat: number;
}) {
  return (
    <>
      <div className="gridLabel stickyCol">{label}</div>
      {months.map((month) => {
        const heat = heatByMonth[month] ?? 0;
        return (
          <div className={`heatCell level${heatLevel(heat, maxHeat)}`} title={`${label} · ${month} · 资料热度 ${heat}`} key={month}>
            {heat || ""}
          </div>
        );
      })}
    </>
  );
}

function CompanyDetail({ company }: { company: Company }) {
  return (
    <aside className="detailPanel">
      <PanelTitle icon={<Star size={17} />} title="公司详情" meta={company.ownership} />
      <div className="companyHero">
        <h2>{company.name}</h2>
        <span>{company.code}</span>
      </div>
      <div className="metricGrid">
        <Metric label="P级" value={company.priority} />
        <Metric label="资料热度" value={String(company.heat)} />
        <Metric label="本地价格" value={company.price || "--"} />
        <Metric label="记录日期" value={company.priceDate || "--"} />
      </div>
      <section className="detailSection">
        <h3>产业链定位</h3>
        <p>{company.chains.join(" / ")}</p>
        <p className="muted">{company.stages.join("、")}</p>
      </section>
      <section className="detailSection">
        <h3>摘要</h3>
        <p>{company.summary || "待补：公司卡中未找到可稳定抽取的摘要。"}</p>
      </section>
      <section className="detailSection">
        <h3>备注</h3>
        {company.notes.length ? company.notes.map((note) => <p key={note}>{note}</p>) : <p className="muted">暂无备注</p>}
      </section>
      <section className="detailSection">
        <h3>反证 / 风险</h3>
        {company.risks.length ? (
          <ul>
            {company.risks.slice(0, 5).map((risk, index) => (
              <li key={`${risk}-${index}`}>{risk}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">待补：未解析到风险条目。</p>
        )}
      </section>
      <section className="detailSection">
        <h3>资料入口</h3>
        <div className="refList">
          {company.sourceRefs.slice(0, 8).map((ref) => (
            <span key={`${ref.target}-${ref.label}`}>{ref.label}</span>
          ))}
          {company.cardPath && <span>公司卡：{company.cardPath}</span>}
        </div>
      </section>
    </aside>
  );
}

function WatchlistPage({
  query,
  priority,
  ownership,
  onSelectCompany
}: {
  query: string;
  priority: string;
  ownership: OwnershipFilter;
  onSelectCompany: (name: string) => void;
}) {
  const items = watchlist.filter((item) => {
    const priorityMatch = priority === "all" || item.priority === priority;
    const ownershipMatch =
      ownership === "all" ||
      (ownership === "holding" && item.ownership.includes("持仓")) ||
      (ownership === "watch" && item.ownership.includes("自选"));
    return priorityMatch && ownershipMatch && matchesWatchlistSearch(item, query);
  });
  const grouped = groupWatchlist(items);
  const groupColumns = splitIntoColumns(Object.entries(grouped), 4);
  return (
    <main className="watchlistLayout">
      <section className="watchHeader">
        <PanelTitle icon={<Table2 size={17} />} title="自选/持仓产业链分类" meta={`${items.length} 个标的`} />
        <p>5日/10日涨跌只基于本地同花顺 raw 历史快照计算；缺少可比日期时显示“本地快照不足”。</p>
      </section>
      <section className="watchGroupsBoard">
        {groupColumns.map((column, index) => (
          <div className="watchGroupColumn" key={`watch-column-${index}`}>
            {column.map(([chain, chainItems]) => (
              <WatchGroup key={chain} chain={chain} items={chainItems} onSelectCompany={onSelectCompany} />
            ))}
          </div>
        ))}
      </section>
    </main>
  );
}

function NotesPage({ companies, onSelectCompany }: { companies: Company[]; onSelectCompany: (name: string) => void }) {
  const noteCompanies = companies.filter(hasCompanyNotes);
  const grouped = groupCompaniesByPrimaryChain(noteCompanies);
  return (
    <main className="notesLayout">
      <section className="notesHeader">
        <PanelTitle icon={<FileText size={17} />} title="笔记整理" meta={`${noteCompanies.length} 条公司笔记`} />
        <p>按产业链聚合公司卡、备注、风险提示和资料入口；内容来自本地 Wiki 缓存，默认保留待核验语气。</p>
      </section>
      <section className="notesBoard">
        {Object.entries(grouped).map(([chain, chainCompanies]) => (
          <section className="notesGroup" key={chain}>
            <div className="notesGroupTitle">
              <h2>{chain}</h2>
              <span>{chainCompanies.length} 条</span>
            </div>
            <div className="noteCards">
              {chainCompanies.map((company) => (
                <button className="noteCard" key={`${company.code}-${company.name}`} onClick={() => onSelectCompany(company.name)}>
                  <div className="noteCardTop">
                    <b>{company.name}</b>
                    <span>{company.priority} · 热{company.heat}</span>
                  </div>
                  <p>{primaryNote(company)}</p>
                  {company.risks.length > 0 && <small>风险/待核验：{trimNote(company.risks[0])}</small>}
                  {company.sourceRefs.length > 0 && <em>来源：{company.sourceRefs[0].label}</em>}
                </button>
              ))}
            </div>
          </section>
        ))}
      </section>
    </main>
  );
}

function hasCompanyNotes(company: Company): boolean {
  return Boolean(company.notes.length || company.risks.length || usefulSummary(company.summary) || company.sourceRefs.length);
}

function usefulSummary(summary: string): boolean {
  return Boolean(summary && !summary.startsWith("待补"));
}

function primaryNote(company: Company): string {
  if (company.notes.length) {
    return trimNote(company.notes[0]);
  }
  if (usefulSummary(company.summary)) {
    return trimNote(company.summary);
  }
  if (company.risks.length) {
    return `待核验：${trimNote(company.risks[0])}`;
  }
  return "暂无明确备注，保留资料入口用于后续补充。";
}

function trimNote(value: string): string {
  return cleanNoteText(value).slice(0, 140);
}

function cleanNoteText(value: string): string {
  let text = value.trim().replace(/^[-\s>]+/, "").trim();
  const embeddedTextField = text.match(/"text"\s*:\s*"([^"]+)"/);
  if (embeddedTextField) {
    text = embeddedTextField[1];
  }
  const textField = text.match(/^"text"\s*:\s*"([\s\S]*)"\s*,?$/);
  if (textField) {
    text = textField[1];
  }
  return text
    .replace(/\\n/g, " ")
    .replace(/\\"/g, '"')
    .replace(/<[^>]+>/g, "")
    .replace(/#+\s*/g, "")
    .replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_match, path: string, alias?: string) => alias || path.split("/").pop() || path)
    .replace(/\s+/g, " ")
    .trim();
}

function groupCompaniesByPrimaryChain(items: Company[]): Record<string, Company[]> {
  const groups: Record<string, Company[]> = {};
  for (const company of items) {
    const chain = company.chains[0] || "未归类";
    groups[chain] ??= [];
    groups[chain].push(company);
  }
  return Object.fromEntries(
    Object.entries(groups).sort(([left], [right]) => left.localeCompare(right, "zh-CN"))
  );
}

function WatchGroup({
  chain,
  items,
  onSelectCompany
}: {
  chain: string;
  items: WatchlistItem[];
  onSelectCompany: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const holdings = items.filter((item) => item.ownership.includes("持仓")).length;
  const watches = items.filter((item) => item.ownership.includes("自选")).length;
  return (
    <section className="watchGroup">
      <button className="watchGroupHeader" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="watchGroupTitle">
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <b>{chain}</b>
        </span>
        <span className="watchGroupMeta">
          {items.length} 标的 · 持仓 {holdings} · 自选 {watches}
        </span>
      </button>
      {open && (
        <div className="watchCompanyList">
          <div className="watchCompanyHeader">
            <span>公司</span>
            <span>代码</span>
            <span>P</span>
            <span>归属</span>
            <span>价格</span>
            <span>热度</span>
          </div>
          {items.map((item) => (
            <WatchCompanyRow key={`${item.code}-${item.name}`} item={item} onSelectCompany={onSelectCompany} />
          ))}
        </div>
      )}
    </section>
  );
}

function WatchCompanyRow({
  item,
  onSelectCompany
}: {
  item: WatchlistItem;
  onSelectCompany: (name: string) => void;
}) {
  return (
    <button
      className="watchCompanyRow"
      onClick={() => onSelectCompany(item.name)}
      title={`${item.name} · 5日 ${formatChange(item.change5d)} · 10日 ${formatChange(item.change10d)}`}
    >
      <span className="watchCompanyName">{item.name}</span>
      <span>{item.code}</span>
      <b>{item.priority}</b>
      <span>{item.ownership}</span>
      <span>{item.price || "--"}</span>
      <span>热{item.heat}</span>
    </button>
  );
}

function groupWatchlist(items: WatchlistItem[]): Record<string, WatchlistItem[]> {
  const groups: Record<string, WatchlistItem[]> = {};
  for (const item of items) {
    const chain = item.chains[0] || "未归类";
    groups[chain] ??= [];
    groups[chain].push(item);
  }
  return Object.fromEntries(
    Object.entries(groups).sort(([left], [right]) => left.localeCompare(right, "zh-CN"))
  );
}

function splitIntoColumns<T>(items: T[], columnCount: number): T[][] {
  return items.reduce<T[][]>((columns, item, index) => {
    columns[index % columnCount].push(item);
    return columns;
  }, Array.from({ length: columnCount }, () => []));
}

function PanelTitle({ icon, title, meta: right }: { icon: React.ReactNode; title: string; meta: string }) {
  return (
    <div className="panelTitle">
      <div>
        {icon}
        <h2>{title}</h2>
      </div>
      <span>{right}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
