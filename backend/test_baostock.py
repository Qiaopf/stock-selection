"""
baostock 数据源测试脚本
无需注册，无需 Token，无频率限制

运行: python test_baostock.py
"""
import baostock as bs
import pandas as pd

print("=" * 60)
print("baostock 数据源测试")
print("=" * 60)

# 1. 登录
lg = bs.login()
print(f"\n[1/4] 登录结果: {lg.error_code} - {lg.error_msg}")

if lg.error_code != '0':
    print("❌ 登录失败，请检查网络")
    exit()

# 2. 获取股票列表
print("\n[2/4] 获取股票列表...")
rs = bs.query_stock_basic()
data = []
while rs.next():
    data.append(rs.get_row_data())

df = pd.DataFrame(data, columns=['代码', '名称', '状态', '上市日期', '退市日期', '类型'])
print(f"    共获取 {len(df)} 只股票")
print(f"    状态分布: {df['状态'].value_counts().to_dict()}")
print(f"    前5只: {df['名称'].head().tolist()}")

# 3. 获取日线数据
print("\n[3/4] 获取平安银行(000001)日线数据...")
rs = bs.query_history_k_data_plus(
    "sz.000001",
    "date,code,open,high,low,close,volume,amount,pctChg",
    start_date="2026-06-01",
    end_date="2026-09-04",
    frequency="d",
    adjustflag="3"
)
data = []
while rs.next():
    data.append(rs.get_row_data())
kline = pd.DataFrame(data, columns=['日期', '代码', '开盘', '最高', '最低', '收盘', '成交量', '成交额', '涨跌幅'])
print(f"    获取 {len(kline)} 条日线数据")
print(f"    数据预览:")
print(kline.to_string(index=False))

# 4. 批量获取测试（模拟选股场景）
print("\n[4/4] 批量获取测试（模拟选股时同时拉100只股票）...")
test_codes = ['sz.000001', 'sz.000002', 'sz.000651', 'sh.600000', 'sh.600036',
              'sz.000333', 'sh.600519', 'sz.000858', 'sh.601318', 'sz.002415']
success = 0
for code in test_codes:
    rs = bs.query_history_k_data_plus(
        code,
        "date,code,close",
        start_date="2026-08-01",
        end_date="2026-09-04",
        frequency="d",
        adjustflag="3"
    )
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    if len(data) > 0:
        success += 1
print(f"    成功获取 {success}/{len(test_codes)} 只股票数据 ✅")

# 登出
bs.logout()
print("\n✅ 测试完成!")