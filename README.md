# 量化选股系统

基于 Python + Vue3 的量化选股系统，支持技术指标选股：MACD金叉 + KDJ金叉。

## 功能特点

- **基础过滤**: 从A股中过滤出非ST、非创业板、非科创板股票
- **技术指标**: 筛选 MACD金叉 和 KDJ金叉 个股
- **可视化**: 交互式前端界面展示选股结果
- **实时数据**: 支持从东方财富获取最新行情数据

## 项目结构

```
stock-selection/
├── backend/                 # Python 后端
│   ├── app.py              # FastAPI 主应用
│   ├── requirements.txt    # Python 依赖
│   ├── stock_selector.py   # 选股逻辑核心
│   └── data_fetcher.py     # 数据获取模块
├── frontend/                # Vue3 前端
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端服务将在 http://localhost:8000 启动

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 http://localhost:5173 启动

## 选股条件

1. **基础过滤**
   - 排除 ST 股票
   - 排除 创业板 (300开头)
   - 排除 科创板 (688开头)

2. **技术指标**
   - **MACD 金叉**: DIF 线上穿 DEA 线
   - **KDJ 金叉**: K 线上穿 D 线

## 技术栈

- **后端**: Python + FastAPI + Tushare / 东方财富API
- **前端**: Vue3 + Vite + Ant Design Vue + ECharts
- **数据**: A股实时行情数据

## License

MIT
