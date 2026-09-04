"""
FastAPI 主应用 - 量化选股系统后端
"""
import json
import os
import time
import traceback
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from data_fetcher import get_stock_list, get_stock_daily
from stock_selector import StockSelector, filter_stock_basics
from indicators import calculate_macd, calculate_kdj, check_macd_golden_cross, check_macd_strict_golden_cross, check_kdj_golden_cross, check_kdj_strict_golden_cross

app = FastAPI(
    title="量化选股系统",
    description="基于 MACD 金叉 + KDJ 金叉的 A 股量化选股系统",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 缓存选股结果
_cached_results = None
_cached_time = None
_CACHE_TTL = 3600  # 缓存有效期 1 小时


class StockResult(BaseModel):
    code: str
    name: str
    latest_price: float
    change_pct: float
    volume: float
    amount: float
    DIF: float
    DEA: float
    MACD: float
    K: float
    D: float
    J: float
    date: str


class StockDetail(BaseModel):
    code: str
    name: str
    dates: list
    closes: list
    opens: list
    highs: list
    lows: list
    volumes: list
    dif: list
    dea: list
    macd: list
    k_values: list
    d_values: list
    j_values: list


@app.get("/")
def root():
    return {
        "name": "量化选股系统",
        "version": "1.0.0",
        "endpoints": {
            "筛选结果": "/api/stocks?strict=true&min_volume=0.5",
            "个股详情": "/api/stock/000001?name=平安银行",
            "股票列表": "/api/stock-list",
            "系统状态": "/api/status"
        }
    }


@app.get("/api/stocks", response_model=list)
async def get_filtered_stocks(
    strict: bool = Query(True, description="严格模式：仅当日刚金叉"),
    min_volume: float = Query(0.5, description="最小成交额（亿元）"),
    force_refresh: bool = Query(False, description="强制刷新缓存")
):
    """
    获取选股结果：MACD金叉 + KDJ金叉
    """
    global _cached_results, _cached_time

    current_time = time.time()

    # 使用缓存
    if not force_refresh and _cached_results is not None and _cached_time is not None:
        if current_time - _cached_time < _CACHE_TTL:
            return _cached_results

    try:
        selector = StockSelector(strict_mode=strict, min_volume=min_volume)
        results = selector.screen_all_stocks()

        _cached_results = results
        _cached_time = current_time

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{code}", response_model=StockDetail)
async def get_stock_detail(
    code: str,
    name: str = Query("", description="股票名称")
):
    """
    获取个股详细数据（含完整技术指标）
    """
    try:
        df = get_stock_daily(code)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")

        # 计算指标
        df = calculate_macd(df)
        df = calculate_kdj(df)

        # 获取名称
        if not name:
            try:
                df_list = get_stock_list()
                if '代码' in df_list.columns:
                    match = df_list[df_list['代码'] == code]
                    if not match.empty:
                        name = str(match.iloc[0]['名称'])
            except:
                pass

        return StockDetail(
            code=code,
            name=name or "未知",
            dates=df['date'].dt.strftime('%Y-%m-%d').tolist(),
            closes=[round(x, 2) for x in df['close'].tolist()],
            opens=[round(x, 2) for x in df['open'].tolist()],
            highs=[round(x, 2) for x in df['high'].tolist()],
            lows=[round(x, 2) for x in df['low'].tolist()],
            volumes=[round(x / 1e4, 2) for x in df['volume'].tolist()],
            dif=[round(x, 4) for x in df['DIF'].tolist()],
            dea=[round(x, 4) for x in df['DEA'].tolist()],
            macd=[round(x, 4) for x in df['MACD'].tolist()],
            k_values=[round(x, 2) for x in df['K'].tolist()],
            d_values=[round(x, 2) for x in df['D'].tolist()],
            j_values=[round(x, 2) for x in df['J'].tolist()],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock-list")
async def get_stock_list_endpoint():
    """
    获取 A 股股票列表
    """
    try:
        df = get_stock_list()
        stocks = []
        for _, row in df.iterrows():
            code = str(row.get('代码', row.get('code', ''))).zfill(6)
            name = str(row.get('名称', row.get('name', '')))
            if code and name:
                stocks.append({
                    'code': code,
                    'name': name,
                    'filtered': not filter_stock_basics(code, name)
                })
        return stocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    global _cached_results, _cached_time

    # baostock 内置股票列表，不需要文件
    total_stocks = -1

    return {
        "status": "running",
        "total_stocks_available": total_stocks,
        "cached_results": len(_cached_results) if _cached_results else 0,
        "cache_time": datetime.fromtimestamp(_cached_time).isoformat() if _cached_time else None,
        "server_time": datetime.now().isoformat()
    }


# ========== 全局异常处理器 ==========
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常捕获，返回详细错误信息"""
    tb = traceback.format_exc()
    print(f"❌ 错误: {str(exc)}")
    print(f"📋 详细堆栈:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "traceback": tb.split('\n')[-20:]  # 返回最后20行堆栈
        }
    )


# ========== 调试接口 ==========
@app.get("/api/debug")
async def debug():
    """调试接口，测试数据源连通性"""
    results = {}
    
    # 1. 测试导入
    results['imports'] = 'ok'
    
    # 2. 检查 baostock
    try:
        import baostock
        results['baostock_version'] = baostock.__version__
    except Exception as e:
        results['baostock_version'] = f"未安装: {e}"
    
    # 3. 测试获取股票列表
    try:
        df = get_stock_list()
        results['stock_list'] = {
            'status': 'ok',
            'count': len(df),
            'columns': list(df.columns)
        }
        # 取前3只展示
        sample = df.head(3)
        if '代码' in df.columns:
            results['stock_list']['sample'] = sample[['代码', '名称']].to_dict('records')
        else:
            results['stock_list']['sample'] = str(sample.to_dict('records'))
    except Exception as e:
        tb = traceback.format_exc()
        results['stock_list'] = {'status': '失败', 'error': str(e), 'traceback': tb.split('\n')[-10:]}
    
    # 4. 测试获取单只股票日线
    try:
        df_daily = get_stock_daily('000001')
        results['stock_daily'] = {
            'status': 'ok' if not df_daily.empty else 'empty',
            'rows': len(df_daily),
            'columns': list(df_daily.columns) if not df_daily.empty else []
        }
    except Exception as e:
        results['stock_daily'] = {'status': '失败', 'error': str(e)}
    
    return results


# ========== 个股金叉诊断接口 ==========
@app.get("/api/debug/check/{code}")
async def debug_check_stock(code: str):
    """诊断单只股票的金叉情况"""
    try:
        # 获取数据和计算指标
        df = get_stock_daily(code)
        if df.empty:
            return {"code": code, "error": "无数据"}

        df = calculate_macd(df)
        df = calculate_kdj(df)

        # 最近3天数据
        recent = df.tail(3)
        rows = []
        for _, row in recent.iterrows():
            rows.append({
                "date": str(row['date'].date()),
                "close": round(row['close'], 3),
                "DIF": round(row['DIF'], 4),
                "DEA": round(row['DEA'], 4),
                "MACD": round(row['MACD'], 4),
                "K": round(row['K'], 2),
                "D": round(row['D'], 2),
                "J": round(row['J'], 2),
            })

        # 判断金叉
        macd_strict = check_macd_strict_golden_cross(df)
        macd_loose = check_macd_golden_cross(df)
        kdj_strict = check_kdj_strict_golden_cross(df)
        kdj_loose = check_kdj_golden_cross(df)

        return {
            "code": code,
            "total_days": len(df),
            "latest_date": str(df.iloc[-1]['date'].date()),
            "recent_3_days": rows,
            "golden_cross": {
                "MACD_严格": macd_strict,
                "MACD_宽松": macd_loose,
                "KDJ_严格": kdj_strict,
                "KDJ_宽松": kdj_loose,
                "双金叉_严格": macd_strict and kdj_strict,
                "双金叉_宽松": macd_loose and kdj_loose,
            }
        }
    except Exception as e:
        tb = traceback.format_exc()
        return {"code": code, "error": str(e), "traceback": tb.split('\n')[-10:]}


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动量化选股系统后端...")
    print("📡 地址: http://localhost:8000")
    print("🔍 调试接口: http://localhost:8000/api/debug")
    uvicorn.run(app, host="0.0.0.0", port=8000)