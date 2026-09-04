"""
数据获取模块 - 使用 akshare 获取 A 股数据
"""
import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional


def get_stock_list() -> pd.DataFrame:
    """获取 A 股股票列表，排除北交所股票"""
    df = ak.stock_zh_a_spot_em()
    if df.empty:
        raise ValueError("获取股票列表失败")
    return df


def get_stock_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取个股日线数据

    Args:
        code: 股票代码，如 "000001"
        start_date: 开始日期，如 "20240801"
        end_date: 结束日期，如 "20240904"

    Returns:
        DataFrame with columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额
    """
    # 默认获取最近 120 个交易日
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=240)).strftime("%Y%m%d")

    try:
        # 判断是沪市还是深市，确定symbol
        # 深市: 000, 001, 002, 300开头
        # 沪市: 600, 601, 603, 605, 688开头
        if code.startswith(('6')):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"

        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date,
                                adjust="qfq")  # 前复权

        if df.empty:
            return pd.DataFrame()

        # 重命名列
        df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)

        return df

    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
        return pd.DataFrame()


def batch_get_stock_daily(codes: list, max_workers: int = 5) -> dict:
    """
    批量获取多只股票日线数据

    Args:
        codes: 股票代码列表
        max_workers: 最大并发数

    Returns:
        {code: DataFrame}
    """
    result = {}
    total = len(codes)

    for i, code in enumerate(codes):
        if i % 10 == 0:
            print(f"进度: {i}/{total}")
        df = get_stock_daily(code)
        if not df.empty:
            result[code] = df
        time.sleep(0.3)  # 避免请求过快

    return result


if __name__ == "__main__":
    # 测试
    df_list = get_stock_list()
    print(f"获取到 {len(df_list)} 只股票")
    print(df_list.head())