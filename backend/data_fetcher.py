"""
数据获取模块 - 使用 TuShare 获取 A 股数据

使用前请先:
1. 去 https://tushare.pro/register 注册（免费）
2. 获取你的 Token
3. 设置环境变量: set TUSHARE_TOKEN=你的token

注意: TuShare 免费版 stock_basic 接口限频 1次/分钟，
      daily 接口限频 200次/分钟。
      股票列表会被缓存到本地文件，避免重复请求。
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

# 缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
STOCK_LIST_CACHE = os.path.join(CACHE_DIR, 'stock_list.csv')
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
    获取 A 股股票列表（带本地缓存，避免频繁调用 TuShare）

    Args:
        force_refresh: 是否强制重新从 TuShare 获取
    """
    if pro is None:
        raise ValueError("请先设置 TUSHARE_TOKEN 环境变量")

    # 如果缓存文件存在且未过期，直接读取
    today = datetime.now().strftime('%Y%m%d')
    if not force_refresh and os.path.exists(STOCK_LIST_CACHE):
        try:
            df = pd.read_csv(STOCK_LIST_CACHE, dtype={'代码': str})
            df['代码'] = df['代码'].str.zfill(6)
            print(f"📂 从缓存读取股票列表，共 {len(df)} 只")
            return df
        except Exception as e:
            print(f"⚠️ 缓存读取失败，重新获取: {e}")

    # 从 TuShare 获取
    try:
        df = pro.stock_basic(exchange='', list_status='L',
                           fields='ts_code,symbol,name,industry,list_date')
        df = df.rename(columns={'symbol': '代码', 'name': '名称'})
        df['代码'] = df['代码'].str.zfill(6)
        print(f"📥 从 TuShare 获取到 {len(df)} 只股票")

        # 保存到本地缓存
        df.to_csv(STOCK_LIST_CACHE, index=False)
        print(f"💾 已缓存到 {STOCK_LIST_CACHE}")

        return df

    except Exception as e:
        # 如果网络请求失败，尝试读取旧缓存
        if os.path.exists(STOCK_LIST_CACHE):
            print(f"⚠️ 获取失败，使用旧缓存: {e}")
            df = pd.read_csv(STOCK_LIST_CACHE, dtype={'代码': str})
            df['代码'] = df['代码'].str.zfill(6)
            return df
        raise


def get_stock_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取个股日线数据

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