# 量化选股系统

基于 Python + Vue3 的量化选股系统，支持技术指标选股：MACD金叉 + KDJ金叉。

## 功能特点

- **基础过滤**: 从A股中过滤出非ST、非创业板、非科创板股票
- **技术指标**: 筛选 MACD金叉 和 KDJ金叉 个股
- **可视化**: 交互式前端界面展示选股结果，带K线图和指标图表
- **实时数据**: 通过 TuShare 获取最新行情数据

## 项目结构

```
stock-selection/
├── backend/                 # Python 后端
│   ├── app.py              # FastAPI 主应用
│   ├── requirements.txt    # Python 依赖
│   ├── stock_selector.py   # 选股逻辑核心
│   ├── data_fetcher.py     # 数据获取模块 (TuShare)
│   └── indicators.py       # MACD/KDJ 指标计算
├── frontend/                # Vue3 前端
│   ├── src/
│   │   ├── App.vue         # 主页面
│   │   └── api/index.js    # API 封装
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 1. 获取 TuShare Token

项目使用 TuShare 获取数据，TuShare 数据接口稳定。

1. 注册账号: https://tushare.pro/register （免费）
2. 在个人中心获取你的 Token
3. 设置环境变量:

**Windows CMD:**
```bash
set TUSHARE_TOKEN=你的token字符串
```

**Windows PowerShell:**
```powershell
$env:TUSHARE_TOKEN="你的token字符串"
```

### 2. 启动后端

```bash
cd backend
python -m pip install -r requirements.txt
python app.py
```

后端服务将在 http://localhost:8000 启动

访问 http://localhost:8000/api/debug 可以测试数据连通性

### 3. 启动前端

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
   - 排除北交所股票

2. **技术指标**
   - **MACD 金叉**: DIF 线上穿 DEA 线
   - **KDJ 金叉**: K 线上穿 D 线

3. **可选参数**
   - `strict=true`: 严格模式，只选择**今日刚刚形成**的金叉
   - `strict=false`: 宽松模式，金叉成立状态均可
   - `min_volume`: 过滤最小成交额（单位：亿元）

## 技术栈

- **后端**: Python + FastAPI + TuShare + Pandas + NumPy
- **前端**: Vue3 + Vite + Ant Design Vue + ECharts
- **数据**: TuShare A股行情数据

## 截图

- 左侧：筛选参数面板
- 中间：选股结果表格，支持搜索、排序、导出
- 点击表格行：弹窗展示K线图 + MACD + KDJ 三图联动

## 常见问题

**Q: 获取不到数据？**
A: 请检查 `TUSHARE_TOKEN` 环境变量是否正确设置，token需要在 https://tushare.pro 获取。

**Q: 选股很慢？**
A: API有限流限制，每次请求间隔0.15秒，500只股票大约需要1分钟，耐心等待即可。

**Q: 东方财富原来接口为什么不用了？**
A: 某些网络环境（公司防火墙）会阻止访问东方财富接口，TuShare 更稳定。

## License

MIT
