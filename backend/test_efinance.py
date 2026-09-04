"""
efinance 数据源测试脚本（备选）
无需注册，无频率限制，底层走东方财富

运行: pip install efinance && python test_efinance.py
"""
import efinance as ef
import pandas as pd

print("=" * 60)
print("efinance 数据源测试")
print("=" * 60)

# 1. 获取股票列表
print("\n[1/3] 获取股票列表...")
df = ef.stock.get_realtime_quotes()
print(f"    共获取 {len(df)} 只股票")
print(f"    前5只: {df[['股票代码', '股票名称']].head().to_string(index=False).replace(chr(10), chr(10)+'    ')}")

# 2. 获取日线
print("\n[2/3] 获取平安银行(000001)日线数据...")
kline = ef.stock.get_quote_history("000001")
print(f"    获取 {len(kline)} 条日线数据")
print(f"    数据预览:")
print(kline.head().to_string(index=False))

# 3. 批量测试
print("\n[3/3] 批量获取测试...")
test_codes = ['000001', '000002', '000651', '600000', '600036', '000333', '600519', '000858', '601318', '002415']
success = 0
for code in test_codes:
    kline = ef.stock.get_quote_history(code)
    if kline is not None and len(kline) > 0:
        success += 1
print(f"    成功获取 {success}/{len(test_codes)} 只股票数据 ✅")

print("\n✅ 测试完成!")