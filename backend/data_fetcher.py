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

import threading
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# ========== 共享连接池（供批量选股多线程使用） ==========
_bs_lock = threading.Lock()
_bs_connected = False


def init_bs_pool():
    """批量选股前初始化 baostock 连接（只 login 一次，多线程共享）"""
    global _bs_connected
    with _bs_lock:
        if not _bs_connected:
            lg = bs.login()
            if lg.error_code != '0':
                raise ConnectionError(f"baostock 登录失败: {lg.error_msg}")
            _bs_connected = True
            print("🔌 baostock 连接池已初始化")


def close_bs_pool():
    """批量选股结束后关闭 baostock 连接"""
    global _bs_connected
    with _bs_lock:
        if _bs_connected:
            bs.logout()
            _bs_connected = False
            print("🔌 baostock 连接池已关闭")


def get_stock_daily_pool(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    使用共享连接查询个股日线（线程安全，需先调 init_bs_pool）

    多个线程共用同一个 baostock 连接，通过锁串行化查询，
    避免 baostock 将并发登录视为攻击。
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")

    # 确定交易所前缀
    prefix = 'sh.' if code.startswith('6') else 'sz.'
    bs_code = f"{prefix}{code}"

    with _bs_lock:
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


# ========== 独立连接模式（供单次调用使用） ==========

def get_stock_list() -> pd.DataFrame:
    """
    获取 A 股股票列表（独立连接，自动 login/logout）
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
    获取个股日线数据（独立连接，自动 login/logout）

    用于个股详情、调试等单次调用场景。
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