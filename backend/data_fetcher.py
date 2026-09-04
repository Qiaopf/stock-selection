"""
数据获取模块 - 使用 TuShare 获取 A 股日线数据

股票列表使用内置的 stock_list_builtin.csv（可手动更新），
不依赖 TuShare 的 stock_basic 接口（免费版限频 1次/小时）。

使用前请先:
1. 去 https://tushare.pro/register 注册（免费）
2. 获取你的 Token
3. 设置环境变量: set TUSHARE_TOKEN=你的token
"""
# 禁用系统代理
import os
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(key, None)

import pandas as pd
import tushare as ts
import time
from datetime import datetime, timedelta
from typing import Optional

# 内置股票列表路径
BUILTIN_LIST = os.path.join(os.path.dirname(__file__), 'stock_list_builtin.csv')

# 日线数据缓存目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# 初始化 Tushare
token = os.environ.get('TUSHARE_TOKEN')
if token:
    pro = ts.pro_api(token)
    print(f"✅ TuShare 初始化成功")
else:
    pro = None
    print("⚠️ 未设置 TUSHARE_TOKEN 环境变量")
    print("   请去 https://tushare.pro/register 注册获取 Token")
    print("   然后执行: set TUSHARE_TOKEN=你的token")


def get_stock_list(force_refresh: bool = False) -> pd.DataFrame:
    """
    获取 A 股股票列表

    从内置的 stock_list_builtin.csv 读取，不会调用 TuShare 的 stock_basic 接口。
    如需更新此列表，请重新运行 tools/update_stock_list.py

    Args:
        force_refresh: 兼容参数，内置列表无需刷新
    """
    if not os.path.exists(BUILTIN_LIST):
        raise FileNotFoundError(
            f"内置股票列表 {BUILTIN_LIST} 不存在，请先运行 tools/update_stock_list.py 生成"
        )

    df = pd.read_csv(BUILTIN_LIST, encoding='utf-8')
    # 从 "000686.SZ" 格式提取 "000686"
    df['代码'] = df['股票代码'].astype(str).str.replace(r'\.(SZ|SH|BJ)$', '', regex=True)
    df = df.rename(columns={'股票简称': '名称'})
    print(f"📂 从内置列表读取，共 {len(df)} 只股票")
    return df[['代码', '名称']]


def get_stock_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取个股日线数据（通过 TuShare daily 接口，仅需 120 积分）

    Args:
        code: 股票代码，如 "000001"
        start_date: 开始日期 "20240801"
        end_date: 结束日期 "20240904"
    """
    if pro is None:
        raise ValueError("请先设置 TUSHARE_TOKEN 环境变量")

    # tushare 格式: 000001.SZ / 600000.SH
    if code.startswith('6'):
        ts_code = f"{code}.SH"
    else:
        ts_code = f"{code}.SZ"

    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=240)).strftime("%Y%m%d")

    try:
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return pd.DataFrame()

        df = df.sort_values('trade_date').reset_index(drop=True)

        df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume',
            'pct_chg': 'pct_change'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

        # 单位转换: amount 千元 → 元, volume 百股 → 股
        df['amount'] = df['amount'] * 1000
        df['volume'] = df['volume'] * 100

        return df

    except Exception as e:
        print(f"⚠️ 获取 {code} 数据失败: {e}")
        return pd.DataFrame()