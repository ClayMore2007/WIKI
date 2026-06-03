# 股票产业链本地 Web App

这个本地应用只读 `ClayMore` 股票 Wiki，生成 `data/cache/*.json`，再用 React 页面展示产业链热力矩阵和自选/持仓分类表。

## 使用

```powershell
npm install
npm run build:cache
npm run dev
```

默认读取：

```text
../ClayMore
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
