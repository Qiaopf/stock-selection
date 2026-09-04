"""
数据获取模块 - 使用 baostock 获取 A 股数据

✅ 无需注册
✅ 无需 Token
✅ 无频率限制
✅ 内置股票列表查询

安装: pip install baostock
"""
# 禁用系统代理
import os
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(key, None)

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def get_stock_list() -> pd.DataFrame:
    """
    获取 A 股股票列表

    baostock 内置股票列表查询，无频率限制。
    code 格式: "sh.600000" 或 "sz.000001"
    """
    lg = bs.login()
    if lg.error_code != '0':
        raise ConnectionError(f"baostock 登录失败: {lg.error_msg}")
    try:
        rs = bs.query_stock_basic()
        data = []
        while rs.next():
            row = rs.get_row_data()
            code = row[0]      # 如 "sh.600000"
            name = row[1]      # 如 "平安银行"
            stock_type = row[4]  # 1=股票, 2=指数
            stock_status = row[5]  # 1=上市, 0=退市

            # 只取上市股票（排除指数）
            if stock_type == '1' and stock_status == '1':
                # 提取纯数字代码
                code_num = code.replace('sh.', '').replace('sz.', '').replace('bj.', '')
                data.append({
                    '代码': code_num,
                    '名称': name,
                    'ts_code': code
                })

        df = pd.DataFrame(data)
        print(f"📂 从 baostock 获取到 {len(df)} 只上市股票")
        return df

    finally:
        bs.logout()


def get_stock_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取个股日线数据（每次调用独立 login/logout，支持多线程并发）

    Args:
        code: 股票代码，如 "000001"
        start_date: 开始日期 "2024-08-01"（YYYY-MM-DD 格式）
        end_date: 结束日期 "2024-09-04"
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")

    # 确定交易所前缀
    prefix = 'sh.' if code.startswith('6') else 'sz.'
    bs_code = f"{prefix}{code}"

    lg = bs.login()
    if lg.error_code != '0':
        raise ConnectionError(f"baostock 登录失败: {lg.error_msg}")
    try:
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,preclose,volume,amount,pctChg",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 不复权
        )

        data = []
        while rs.next():
            row = rs.get_row_data()
            if row[0] == '':
                continue
            data.append(row)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'date', 'code', 'open', 'high', 'low', 'close',
            'pre_close', 'volume', 'amount', 'pct_change'
        ])

        # 类型转换
        for col in ['open', 'high', 'low', 'close', 'pre_close', 'volume', 'amount', 'pct_change']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        return df

    except Exception as e:
        print(f"⚠️ 获取 {code} 数据失败: {e}")
        return pd.DataFrame()

    finally:
        bs.logout()