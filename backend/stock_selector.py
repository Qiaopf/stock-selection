"""
核心选股模块
筛选条件:
1. 非 ST 股票
2. 非创业板 (300 开头)
3. 非科创板 (688 开头)
4. MACD 金叉
5. KDJ 金叉
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import pandas as pd

from data_fetcher import get_stock_list, get_stock_daily, get_stock_daily_pool, init_bs_pool, close_bs_pool
from indicators import (
    calculate_macd,
    calculate_kdj,
    check_macd_strict_golden_cross,
    check_kdj_strict_golden_cross,
    check_macd_golden_cross,
    check_kdj_golden_cross
)

# 选股进度跟踪（供前端轮询）
select_progress = {
    "running": False,
    "total": 0,
    "current": 0,
    "found": 0,
    "message": ""
}
_progress_lock = threading.Lock()  # 多线程进度更新锁


def filter_stock_basics(code: str, name: str) -> bool:
    """
    基础过滤: 排除 ST、创业板、科创板
    """
    # 排除创业板、科创板、北交所
    if code.startswith(('300', '688', '8', '4')):
        return False
    # 排除 ST 股票
    if 'ST' in name.upper() or '退' in name:
        return False
    return True


class StockSelector:
    def __init__(self, strict_mode: bool = True, min_volume: Optional[float] = None, max_stocks: int = 99999):
        self.strict_mode = strict_mode
        self.min_volume = min_volume  # 单位: 亿元
        self.max_stocks = max_stocks  # 最多检查的股票数

    def screen_one_stock(self, code: str, name: str, use_pool: bool = False) -> Optional[Dict]:
        """筛选单只股票

        Args:
            use_pool: True=使用共享连接池（批量选股），False=独立连接（单次调用）
        """
        # 获取日线数据
        if use_pool:
            df = get_stock_daily_pool(code)
        else:
            df = get_stock_daily(code)
        if len(df) < 30:
            return None

        # 过滤最小成交额
        if self.min_volume is not None and self.min_volume > 0 and 'amount' in df.columns:
            latest_amount = df.iloc[-1]['amount'] / 1e8
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

            return {
                'code': code,
                'name': name,
                'latest_price': round(latest['close'], 2),
                'change_pct': round(latest.get('pct_change', 0), 2),
                'volume': round(latest.get('volume', 0) / 1e6, 2),  # 股 → 万手 (1万手=100万股)
                'amount': round(latest.get('amount', 0) / 1e8, 2),  # 元 → 亿元
                'DIF': round(latest['DIF'], 4),
                'DEA': round(latest['DEA'], 4),
                'MACD': round(latest['MACD'], 4),
                'K': round(latest['K'], 2),
                'D': round(latest['D'], 2),
                'J': round(latest['J'], 2),
                'date': str(latest['date'].date())
            }

        return None

    def screen_all_stocks(self) -> List[Dict]:
        """全市场选股（多线程并发，加速 baostock 查询）"""
        # 获取全部股票列表
        print("📥 正在获取 A 股股票列表...")
        df_all = get_stock_list()
        total = len(df_all)
        print(f"✅ 获取到 {total} 只股票")

        # 先筛选出符合基础条件的股票
        candidates = []
        for _, row in df_all.iterrows():
            if '代码' in df_all.columns:
                code = str(row['代码']).zfill(6)
                name = str(row['名称'])
            else:
                code = str(row.get('code', '')).zfill(6)
                name = str(row.get('name', ''))

            if len(code) < 6:
                continue

            # 基础过滤
            if filter_stock_basics(code, name):
                candidates.append({'code': code, 'name': name})

        print(f"📊 基础过滤后剩余 {len(candidates)} 只候选股票")

        # 限制候选数量
        if len(candidates) > self.max_stocks:
            print(f"⚠️ 限制最多检查 {self.max_stocks} 只")
            candidates = candidates[:self.max_stocks]

        total_candidates = len(candidates)

        # 初始化进度
        select_progress["running"] = True
        select_progress["total"] = total_candidates
        select_progress["current"] = 0
        select_progress["found"] = 0
        select_progress["message"] = f"正在筛选 {total_candidates} 只候选股票..."

        # 多线程并发查询（使用共享连接池，避免 baostock 拉黑）
        results = []
        max_workers = 8  # 并发线程数（实际查询串行，计算并行）
        print(f"🚀 启动 {max_workers} 个线程并发查询...")

        # 初始化共享连接池
        init_bs_pool()

        def _check_one(stock):
            """工作线程函数：检查单只股票"""
            try:
                code = stock['code']
                name = stock['name']
                result = self.screen_one_stock(code, name, use_pool=True)
                return (code, name, result)
            except Exception as e:
                print(f"⚠️ {stock['code']} {stock['name']} 检查失败: {e}")
                return (stock['code'], stock['name'], None)

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {executor.submit(_check_one, stock): stock for stock in candidates}

                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    code, name, result = future.result()

                    with _progress_lock:
                        select_progress["current"] = completed
                        if result:
                            results.append(result)
                            select_progress["found"] = len(results)

                    # 进度提示
                    if completed % 50 == 0:
                        with _progress_lock:
                            found = select_progress["found"]
                        print(f"⏳ 进度: {completed}/{total_candidates}, 已找到 {found} 只")

        finally:
            close_bs_pool()  # 关闭共享连接池
            select_progress["running"] = False
            select_progress["message"] = f"选股完成，共找到 {len(results)} 只"

        print(f"🏁 选股完成（{len(results)} 只），耗时已大幅缩短")
        return results


if __name__ == "__main__":
    selector = StockSelector(strict_mode=True, min_volume=0.5)
    results = selector.screen_all_stocks()
    print("\n=== 选股结果 ===")
    for r in results:
        print(f"{r['code']} {r['name']} 价格:{r['latest_price']} 涨幅:{r['change_pct']}%")