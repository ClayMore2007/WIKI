# 股票产业链本地 Web App

这个本地应用只读 `ClayMore` 股票 Wiki，生成 `data/cache/*.json`，再用 React 页面展示产业链热力矩阵和自选/持仓分类表。

## 使用

```powershell
npm install
npm run open
```

快捷脚本会在缓存缺失时刷新数据，复用已运行的 `5173` 服务，必要时再启动 Vite，并用系统默认浏览器打开页面。需要强制刷新缓存时：

```powershell
..\open-stock.ps1 -RefreshCache
```

手动流程：

```powershell
npm install
npm run build:cache
npm run dev
```

Agent 默认流程：

1. 优先在 `APP/stock/` 下运行 `npm run open`。
2. 如需强制刷新缓存，运行 `..\open-stock.ps1 -RefreshCache`。
3. 用系统默认浏览器打开 `http://127.0.0.1:5173`。

除非用户明确要求在 Codex app 内查看，否则不要使用 Codex 内置浏览器。

默认读取：

```text
../../ClayMore
```

打开：

```text
http://127.0.0.1:5173
```

## 数据边界

- 不读取 `ClayMore-Private-Wiki/`。
- 不接外部行情、财报或评级 API。
- 不改写 ClayMore Wiki 原文件。
- 本地价格和涨跌只来自同花顺 raw 历史快照；快照不足时显示“本地快照不足”。
- 资料热度只表示 Wiki 资料出现频率，不代表实时市场热度、订单确认、业绩确认或投资建议。

## 验证

```powershell
python scripts\test_build_stock_cache.py
npm test
npm run build
```
