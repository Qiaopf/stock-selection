"""
核心选股模块
筛选条件:
1. 非 ST 股票
2. 非创业板 (300 开头)
3. 非科创板 (688 开头)
4. MACD 金叉
5. KDJ 金叉
"""
import pandas as pd
import time
from typing import List, Dict, Optional

from data_fetcher import get_stock_list, get_stock_daily
from indicators import (
    calculate_macd,
    calculate_kdj,
    check_macd_strict_golden_cross,
    check_kdj_strict_golden_cross,
    check_macd_golden_cross,
    check_kdj_golden_cross
)


def filter_stock_basics(code: str, name: str) -> bool:
    """
    基础过滤: 排除 ST、创业板、科创板

    规则:
    - 排除名称含 'ST' 的股票
    - 排除 300 开头 (创业板)
    - 排除 688 开头 (科创板)
    """
    # 排除创业板、科创板
    if code.startswith('300') or code.startswith('688'):
        return False

    # 排除 ST 股票
    if 'ST' in name:
        return False

    return True


class StockSelector:
    def __init__(self, strict_mode: bool = True, min_volume: Optional[float] = None):
        """
        初始化选股器

        Args:
            strict_mode: 是否严格只选当日刚金叉，False 则接受已在金叉状态
            min_volume: 最小成交额（亿元），None 不过滤
        """
        self.strict_mode = strict_mode
        self.min_volume = min_volume  # 单位: 亿元

    def screen_one_stock(self, code: str, name: str) -> Optional[Dict]:
        """
        筛选单只股票

        Returns:
            若符合条件返回信息字典，否则返回 None
        """
        # 第一步: 基础过滤
        if not filter_stock_basics(code, name):
            return None

        # 获取日线数据
        df = get_stock_daily(code)
        if len(df) < 30:  # 数据太少跳过
            return None

        # 过滤最小成交额（最近一日）
        if self.min_volume is not None and 'amount' in df.columns:
            latest_amount = df.iloc[-1]['amount'] / 1e8  # 转换为亿元
            if latest_amount < self.min_volume:
                return None

        # 计算指标
        df = calculate_macd(df)
        df = calculate_kdj(df)

        # 判断金叉
        if self.strict_mode:
            macd_golden = check_macd_strict_golden_cross(df)
            kdj_golden = check_kdj_strict_golden_cross(df)
        else:
            macd_golden = check_macd_golden_cross(df)
            kdj_golden = check_kdj_golden_cross(df)

        if macd_golden and kdj_golden:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else latest

            return {
                'code': code,
                'name': name,
                'latest_price': round(latest['close'], 2),
                'change_pct': round(latest.get('pct_change', 0), 2),
                'volume': round(latest.get('volume', 0) / 1e4, 2),  # 万手
                'amount': round(latest.get('amount', 0) / 1e8, 2),  # 亿元
                'DIF': round(latest['DIF'], 4),
                'DEA': round(latest['DEA'], 4),
                'MACD': round(latest['MACD'], 4),
                'K': round(latest['K'], 2),
                'D': round(latest['D'], 2),
                'J': round(latest['J'], 2),
                'date': str(latest['date'].date())
            }

        return None

    def screen_all_stocks(self, progress_callback=None) -> List[Dict]:
        """
        全市场选股

        Args:
            progress_callback: 进度回调函数 callback(current, total)
        """
        # 获取全部股票列表
        df_all = get_stock_list()
        total = len(df_all)
        results = []

        print(f"开始选股，共 {total} 只股票...")

        for idx, (_, row) in enumerate(df_all.iterrows()):
            # akshare 返回列名可能不同
            if '代码' in df_all.columns:
                code = str(row['代码']).zfill(6)
                name = str(row['名称'])
                latest_price = row.get('最新价', 0)
            else:
                code = str(row.get('code', '')).zfill(6)
                name = str(row.get('name', ''))
                latest_price = row.get('trade', 0)

            # 跳过格式不对的
            if len(code) < 6:
                continue

            # 回调进度
            if progress_callback:
                progress_callback(idx + 1, total)

            # 基础过滤在 screen_one_stock 内部已经做了
            result = self.screen_one_stock(code, name)
            if result:
                results.append(result)
                print(f"找到符合条件: {code} {name}")

            # 控制请求频率
            time.sleep(0.1)

            if (idx + 1) % 100 == 0:
                print(f"已完成 {idx + 1}/{total}, 当前找到 {len(results)} 只")

        print(f"选股完成，共找到 {len(results)} 只符合条件的股票")
        return results


if __name__ == "__main__":
    # 测试: 全市场选股
    selector = StockSelector(strict_mode=True, min_volume=0.5)
    results = selector.screen_all_stocks()

    print("\n=== 选股结果 ===")
    for r in results:
        print(f"{r['code']} {r['name']} 价格:{r['latest_price']} 涨幅:{r['change_pct']}%")
