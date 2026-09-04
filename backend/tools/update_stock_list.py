#!/usr/bin/env python
"""
更新内置股票列表

当你需要更新整个A股列表时执行：

cd backend/tools
python update_stock_list.py

注意：需要你登录 TuShare 并且有足够积分获取 stock_basic 接口
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import tushare as ts

token = os.environ.get('TUSHARE_TOKEN')
if not token:
    print("❌ 请先设置 TUSHARE_TOKEN 环境变量")
    sys.exit(1)

pro = ts.pro_api(token)

print("正在从 TuShare 获取 stock_basic...")
df = pro.stock_basic(exchange='', list_status='L',
                   fields='ts_code,symbol,name,industry,list_date')

# 格式转换
df = df.rename(columns={'ts_code': '股票代码', 'name': '股票简称'})
output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stock_list_builtin.csv')

df.to_csv(output_file, index=False, encoding='utf-8')

print(f"✅ 更新完成，共 {len(df)} 只股票")
print(f"文件: {output_file}")
