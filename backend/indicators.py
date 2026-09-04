"""
技术指标计算模块 - MACD 和 KDJ 计算
"""
import pandas as pd
import numpy as np


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算 MACD 指标

    Args:
        df: 包含 'close' 列的 DataFrame
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)

    Returns:
        添加了 'DIF', 'DEA', 'MACD' 列的 DataFrame
    """
    df = df.copy()

    # 计算 EMA
    df['EMA12'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=slow, adjust=False).mean()

    # DIF = EMA12 - EMA26
    df['DIF'] = df['EMA12'] - df['EMA26']

    # DEA = DIF 的 9 日 EMA
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # MACD 柱 = 2 * (DIF - DEA)
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    return df


def check_macd_golden_cross(df: pd.DataFrame) -> bool:
    """
    判断最近一个交易日是否为 MACD 金叉

    MACD 金叉条件: DIF 上穿 DEA
    - 前一日 DIF < 前一日 DEA
    - 当日 DIF > 当日 DEA

    Returns:
        True 表示金叉
    """
    if len(df) < 2:
        return False

    if 'DIF' not in df.columns or 'DEA' not in df.columns:
        df = calculate_macd(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 金叉: DIF 上穿 DEA
    if prev['DIF'] < prev['DEA'] and latest['DIF'] > latest['DEA']:
        return True

    # 连续处于金叉状态 (DIF 已在 DEA 上方)
    if latest['DIF'] > latest['DEA']:
        return True

    return False


def check_macd_strict_golden_cross(df: pd.DataFrame) -> bool:
    """
    严格判断: 仅在最近一个交易日刚刚形成金叉
    """
    if len(df) < 2:
        return False

    if 'DIF' not in df.columns or 'DEA' not in df.columns:
        df = calculate_macd(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 严格金叉: 前一日 DIF < DEA, 当日 DIF > DEA
    return prev['DIF'] < prev['DEA'] and latest['DIF'] > latest['DEA']


def calculate_kdj(df: pd.DataFrame, n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 指标

    Args:
        df: 包含 'high', 'low', 'close' 列的 DataFrame
        n: RSV 周期 (默认9)
        k_smooth: K 值平滑因子 (默认3)
        d_smooth: D 值平滑因子 (默认3)

    Returns:
        添加了 'RSV', 'K', 'D', 'J' 列的 DataFrame
    """
    df = df.copy()

    # 计算 RSV
    low_n = df['low'].rolling(window=n).min()
    high_n = df['high'].rolling(window=n).max()

    df['RSV'] = ((df['close'] - low_n) / (high_n - low_n)) * 100

    # 处理除零情况
    df['RSV'] = df['RSV'].fillna(50)

    # 初始化 K, D, J
    df['K'] = 50.0
    df['D'] = 50.0
    df['J'] = 50.0

    # 递推计算 K, D, J
    for i in range(len(df)):
        if i == 0:
            df.loc[df.index[i], 'K'] = 50.0
            df.loc[df.index[i], 'D'] = 50.0
        else:
            rsv = df.loc[df.index[i], 'RSV']
            prev_k = df.loc[df.index[i - 1], 'K']
            prev_d = df.loc[df.index[i - 1], 'D']

            k = (2.0 / k_smooth) * prev_k + (1.0 / k_smooth) * rsv
            d = (2.0 / d_smooth) * prev_d + (1.0 / d_smooth) * k
            j = 3.0 * k - 2.0 * d

            df.loc[df.index[i], 'K'] = k
            df.loc[df.index[i], 'D'] = d
            df.loc[df.index[i], 'J'] = j

    return df


def check_kdj_golden_cross(df: pd.DataFrame) -> bool:
    """
    判断最近一个交易日是否为 KDJ 金叉

    KDJ 金叉条件: K 线上穿 D 线
    - 前一日 K < 前一日 D
    - 当日 K > 当日 D

    Returns:
        True 表示金叉
    """
    if len(df) < 2:
        return False

    if 'K' not in df.columns or 'D' not in df.columns:
        df = calculate_kdj(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 金叉: K 上穿 D
    if prev['K'] < prev['D'] and latest['K'] > latest['D']:
        return True

    # 连续处于金叉状态
    if latest['K'] > latest['D']:
        return True

    return False


def check_kdj_strict_golden_cross(df: pd.DataFrame) -> bool:
    """
    严格判断: 仅在最近一个交易日刚刚形成 KDJ 金叉
    """
    if len(df) < 2:
        return False

    if 'K' not in df.columns or 'D' not in df.columns:
        df = calculate_kdj(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 严格金叉: 前一日 K < D, 当日 K > D
    return prev['K'] < prev['D'] and latest['K'] > latest['D']


if __name__ == "__main__":
    # 测试
    test_data = pd.DataFrame({
        'close': [10, 11, 12, 11, 13, 14, 15, 14, 16, 17],
        'high': [11, 12, 13, 12, 14, 15, 16, 15, 17, 18],
        'low': [9, 10, 11, 10, 12, 13, 14, 13, 15, 16]
    })

    df_macd = calculate_macd(test_data)
    print("MACD 计算结果:")
    print(df_macd[['close', 'DIF', 'DEA', 'MACD']])

    df_kdj = calculate_kdj(test_data)
    print("\nKDJ 计算结果:")
    print(df_kdj[['close', 'K', 'D', 'J']])

    print(f"\nMACD 金叉: {check_macd_golden_cross(df_macd)}")
    print(f"KDJ 金叉: {check_kdj_golden_cross(df_kdj)}")