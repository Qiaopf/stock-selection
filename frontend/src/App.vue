<template>
  <a-config-provider :locale="locale">
    <div class="app-container">
      <!-- 顶部导航 -->
      <a-layout-header class="app-header">
        <div class="header-content">
          <div class="header-left">
            <span class="logo-icon">📊</span>
            <h1 class="app-title">量化选股系统</h1>
            <a-tag color="blue">MACD 金叉 + KDJ 金叉</a-tag>
          </div>
          <div class="header-right">
            <a-badge :count="stocks.length" :overflow-count="999">
              <a-button type="primary" ghost @click="fetchStocks" :loading="loading">
                <template #icon><ReloadOutlined /></template>
                开始选股
              </a-button>
            </a-badge>
          </div>
        </div>
      </a-layout-header>

      <!-- 主体内容 -->
      <a-layout-content class="app-content">
        <!-- 筛选条件面板 -->
        <a-card class="filter-card" :bordered="false">
          <a-space size="large" wrap>
            <a-form-item label="选股模式">
              <a-radio-group v-model:value="filters.strict" button-style="solid">
                <a-radio-button :value="true">严格模式（当日金叉）</a-radio-button>
                <a-radio-button :value="false">宽松模式（金叉状态）</a-radio-button>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="最低成交额">
              <a-select v-model:value="filters.min_volume" style="width: 140px">
                <a-select-option :value="0">不限</a-select-option>
                <a-select-option :value="0.3">≥ 0.3 亿</a-select-option>
                <a-select-option :value="0.5">≥ 0.5 亿</a-select-option>
                <a-select-option :value="1">≥ 1 亿</a-select-option>
                <a-select-option :value="5">≥ 5 亿</a-select-option>
                <a-select-option :value="10">≥ 10 亿</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="刷新">
              <a-switch v-model:checked="filters.force_refresh" checked-children="强制" un-checked-children="缓存" />
            </a-form-item>
          </a-space>
        </a-card>

        <!-- 进度提示 -->
        <a-alert v-if="progressText && loading" :message="progressText" type="info" show-icon :closable="false" style="margin-bottom: 16px" />

        <!-- 统计信息 -->
        <a-row :gutter="16" class="stats-row">
          <a-col :span="8">
            <a-statistic title="双金叉选股结果" :value="stocks.length" :value-style="{ color: '#1890ff' }">
              <template #prefix><StockOutlined /></template>
            </a-statistic>
          </a-col>
          <a-col :span="8">
            <a-statistic title="选股模式" :value="filters.strict ? '严格（当日金叉）' : '宽松（金叉状态）'" />
          </a-col>
          <a-col :span="8">
            <a-statistic title="数据更新时间" :value="lastUpdateTime" />
          </a-col>
        </a-row>

        <!-- 选股结果表格 -->
        <a-card title="选股结果" :bordered="false">
          <template #extra>
            <a-space>
              <a-input-search
                v-model:value="searchText"
                placeholder="搜索股票代码或名称"
                style="width: 200px"
                @search="onSearch"
              />
              <a-button @click="exportData" :disabled="stocks.length === 0">
                <template #icon><DownloadOutlined /></template>
                导出 CSV
              </a-button>
            </a-space>
          </template>
          <a-table
            :data-source="filteredStocks"
            :columns="columns"
            :loading="loading"
            row-key="code"
            :pagination="{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 只` }"
            :scroll="{ x: 1200 }"
            size="middle"
            @rowClick="showDetail"
            :row-class-name="() => 'clickable-row'"
          >
            <!-- 涨跌幅列 - 颜色标记 -->
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'change_pct'">
                <span :style="{ color: record.change_pct >= 0 ? '#f5222d' : '#52c41a', fontWeight: 'bold' }">
                  {{ record.change_pct >= 0 ? '+' : '' }}{{ record.change_pct }}%
                </span>
              </template>
              <template v-if="column.key === 'macd_status'">
                <a-tag color="green">金叉✓</a-tag>
              </template>
              <template v-if="column.key === 'kdj_status'">
                <a-tag color="green">金叉✓</a-tag>
              </template>
              <template v-if="column.key === 'action'">
                <a-button type="link" size="small" @click="showDetail(record)">
                  查看详情
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-layout-content>

      <!-- 个股详情弹窗 -->
      <a-modal
        v-model:visible="detailVisible"
        :title="`${detailData.name} (${detailData.code})`"
        :footer="null"
        width="90%"
        :style="{ maxWidth: '1200px' }"
        destroy-on-close
      >
        <div v-if="detailLoading" style="text-align: center; padding: 100px 0">
          <a-spin size="large" />
          <p style="margin-top: 16px; color: #999">加载个股数据中...</p>
        </div>
        <div v-else-if="detailError" style="text-align: center; padding: 100px 0">
          <a-result status="error" title="数据加载失败" :sub-title="detailError" />
        </div>
        <div v-else-if="chartData.dates.length > 0">
          <!-- 基础信息 -->
          <a-descriptions :column="4" size="small" bordered style="margin-bottom: 16px">
            <a-descriptions-item label="最新价">{{ detailData.latest_price || chartData.closes.slice(-1)[0] }}</a-descriptions-item>
            <a-descriptions-item label="MACD">
              DIF: {{ chartData.dif.slice(-1)[0] }} | DEA: {{ chartData.dea.slice(-1)[0] }}
            </a-descriptions-item>
            <a-descriptions-item label="KDJ">
              K: {{ chartData.k_values.slice(-1)[0] }} | D: {{ chartData.d_values.slice(-1)[0] }} | J: {{ chartData.j_values.slice(-1)[0] }}
            </a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag color="green">MACD金叉 + KDJ金叉</a-tag>
            </a-descriptions-item>
          </a-descriptions>

          <!-- K线图 -->
          <div ref="klineChartRef" style="height: 500px; width: 100%"></div>
          <!-- MACD 图 -->
          <div ref="macdChartRef" style="height: 200px; width: 100%; margin-top: 8px"></div>
          <!-- KDJ 图 -->
          <div ref="kdjChartRef" style="height: 200px; width: 100%; margin-top: 8px"></div>
        </div>
      </a-modal>
    </div>
  </a-config-provider>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import {
  ReloadOutlined,
  StockOutlined,
  DownloadOutlined,
} from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import { getFilteredStocks, getStockDetail, getProgress } from './api/index.js'

// 语言包
const locale = zhCN

// 状态
const stocks = ref([])
const loading = ref(false)
const searchText = ref('')
const progressText = ref('')
const lastUpdateTime = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detailData = ref({})
const chartData = ref({
  dates: [], closes: [], opens: [], highs: [], lows: [], volumes: [],
  dif: [], dea: [], macd: [],
  k_values: [], d_values: [], j_values: []
})
const klineChartRef = ref(null)
const macdChartRef = ref(null)
const kdjChartRef = ref(null)

let klineChart = null
let macdChart = null
let kdjChart = null
const resizeHandlers = []

// 筛选条件
const filters = reactive({
  strict: true,
  min_volume: 0.5,
  force_refresh: false
})

// 表格列定义
const columns = [
  { title: '股票代码', dataIndex: 'code', key: 'code', width: 100, fixed: 'left' },
  { title: '股票名称', dataIndex: 'name', key: 'name', width: 120, fixed: 'left' },
  { title: '最新价', dataIndex: 'latest_price', key: 'latest_price', width: 100, sorter: (a, b) => a.latest_price - b.latest_price },
  { title: '涨跌幅', dataIndex: 'change_pct', key: 'change_pct', width: 100, sorter: (a, b) => a.change_pct - b.change_pct },
  { title: '成交额(亿)', dataIndex: 'amount', key: 'amount', width: 110, sorter: (a, b) => a.amount - b.amount },
  { title: '成交量(万手)', dataIndex: 'volume', key: 'volume', width: 110 },
  { title: 'DIF', dataIndex: 'DIF', key: 'DIF', width: 100 },
  { title: 'DEA', dataIndex: 'DEA', key: 'DEA', width: 100 },
  { title: 'MACD柱', dataIndex: 'MACD', key: 'MACD', width: 100 },
  { title: 'K值', dataIndex: 'K', key: 'K', width: 80 },
  { title: 'D值', dataIndex: 'D', key: 'D', width: 80 },
  { title: 'J值', dataIndex: 'J', key: 'J', width: 80 },
  { title: 'MACD', dataIndex: 'macd_status', key: 'macd_status', width: 90 },
  { title: 'KDJ', dataIndex: 'kdj_status', key: 'kdj_status', width: 90 },
  { title: '操作', dataIndex: 'action', key: 'action', width: 100, fixed: 'right' }
]

// 搜索过滤
const filteredStocks = computed(() => {
  if (!searchText.value) return stocks.value
  const keyword = searchText.value.toUpperCase()
  return stocks.value.filter(s =>
    s.code.includes(keyword) || s.name.toUpperCase().includes(keyword)
  )
})

// 获取选股结果
async function fetchStocks() {
  loading.value = true
  progressText.value = '正在获取股票列表...'
  try {
    // 启动进度轮询
    let pollTimer = setInterval(async () => {
      try {
        const p = await getProgress()
        if (p.running) {
          progressText.value = `正在筛选第 ${p.current}/${p.total} 只，已找到 ${p.found} 只`
        }
      } catch (_) { /* ignore polling errors */ }
    }, 2000)

    const result = await getFilteredStocks({
      strict: filters.strict,
      min_volume: filters.min_volume,
      force_refresh: filters.force_refresh
    })
    clearInterval(pollTimer)
    stocks.value = result
    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
    message.success(`选股完成，共找到 ${result.length} 只符合条件的股票`)
  } catch (err) {
    progressText.value = ''
    message.error('选股失败: ' + (err.message || '请检查后端服务是否启动'))
  } finally {
    loading.value = false
    progressText.value = ''
  }
}

// 搜索
function onSearch() {
  // 计算属性会自动处理
}

// 导出 CSV
function exportData() {
  const headers = ['股票代码', '股票名称', '最新价', '涨跌幅', '成交额(亿)', '成交量(万手)', 'DIF', 'DEA', 'MACD', 'K值', 'D值', 'J值']
  const rows = filteredStocks.value.map(s => [
    s.code, s.name, s.latest_price, s.change_pct, s.amount, s.volume,
    s.DIF, s.DEA, s.MACD, s.K, s.D, s.J
  ])
  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `选股结果_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  message.success('导出成功')
}

// 显示个股详情
async function showDetail(record) {
  detailData.value = record
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = ''

  try {
    const data = await getStockDetail(record.code, record.name)
    chartData.value = data
    detailLoading.value = false

    await nextTick()
    renderCharts(data)
  } catch (err) {
    detailLoading.value = false
    detailError.value = err.message || '获取数据失败'
  }
}

// 渲染图表
function renderCharts(data) {
  if (!data.dates || data.dates.length === 0) return

  // 清理旧图表
  if (klineChart) klineChart.dispose()
  if (macdChart) macdChart.dispose()
  if (kdjChart) kdjChart.dispose()

  renderKlineChart(data)
  renderMacdChart(data)
  renderKdjChart(data)
}

function renderKlineChart(data) {
  if (!klineChartRef.value) return
  klineChart = echarts.init(klineChartRef.value)

  // K线数据
  const klineData = data.dates.map((_, i) => [
    data.opens[i], data.closes[i], data.lows[i], data.highs[i]
  ])

  // 成交量颜色
  const volumeColors = data.dates.map((_, i) => {
    return i > 0 && data.closes[i] >= data.closes[i - 1]
      ? '#ef5350' : '#26a69a'
  })

  const option = {
    backgroundColor: '#fff',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    grid: [
      { left: '8%', right: '8%', top: '8%', height: '60%' },
      { left: '8%', right: '8%', top: '78%', height: '15%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: data.dates,
        gridIndex: 0,
        axisLabel: { rotate: 45, fontSize: 10 },
        splitLine: { show: false }
      },
      {
        type: 'category',
        data: data.dates,
        gridIndex: 1,
        axisLabel: { show: false },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true, splitArea: { show: true } },
      { type: 'value', gridIndex: 1, splitNumber: 2, axisLabel: { show: true } }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: klineData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: data.volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: volumeColors[i] }
        }))
      }
    ]
  }

  klineChart.setOption(option)
  const handler = () => klineChart.resize()
  window.addEventListener('resize', handler)
  resizeHandlers.push(handler)
}

function renderMacdChart(data) {
  if (!macdChartRef.value) return
  macdChart = echarts.init(macdChartRef.value)

  const macdColors = data.macd.map(v => v >= 0 ? '#ef5350' : '#26a69a')

  const option = {
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis' },
    grid: { left: '8%', right: '8%', top: '15%', bottom: '12%' },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: { type: 'value', splitLine: { show: true } },
    series: [
      {
        name: 'DIF',
        type: 'line',
        data: data.dif,
        lineStyle: { color: '#1890ff', width: 1.5 },
        symbol: 'none'
      },
      {
        name: 'DEA',
        type: 'line',
        data: data.dea,
        lineStyle: { color: '#f5222d', width: 1.5 },
        symbol: 'none'
      },
      {
        name: 'MACD',
        type: 'bar',
        data: data.macd.map((v, i) => ({
          value: v,
          itemStyle: { color: macdColors[i] }
        })),
        barWidth: '60%'
      }
    ]
  }

  macdChart.setOption(option)
  const handler = () => macdChart.resize()
  window.addEventListener('resize', handler)
  resizeHandlers.push(handler)
}

function renderKdjChart(data) {
  if (!kdjChartRef.value) return
  kdjChart = echarts.init(kdjChartRef.value)

  const option = {
    backgroundColor: '#fff',
    tooltip: { trigger: 'axis' },
    grid: { left: '8%', right: '8%', top: '15%', bottom: '12%' },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { show: true },
      axisLabel: { show: true }
    },
    series: [
      {
        name: 'K',
        type: 'line',
        data: data.k_values,
        lineStyle: { color: '#1890ff', width: 1.5 },
        symbol: 'none'
      },
      {
        name: 'D',
        type: 'line',
        data: data.d_values,
        lineStyle: { color: '#f5222d', width: 1.5 },
        symbol: 'none'
      },
      {
        name: 'J',
        type: 'line',
        data: data.j_values,
        lineStyle: { color: '#52c41a', width: 1.5 },
        symbol: 'none'
      },
      {
        name: '超买线',
        type: 'line',
        data: Array(data.dates.length).fill(80),
        lineStyle: { color: '#ff4d4f', width: 1, type: 'dashed' },
        symbol: 'none'
      },
      {
        name: '超卖线',
        type: 'line',
        data: Array(data.dates.length).fill(20),
        lineStyle: { color: '#52c41a', width: 1, type: 'dashed' },
        symbol: 'none'
      }
    ]
  }

  kdjChart.setOption(option)
  const handler = () => kdjChart.resize()
  window.addEventListener('resize', handler)
  resizeHandlers.push(handler)
}

// 监听弹窗关闭销毁图表
watch(detailVisible, (val) => {
  if (!val) {
    setTimeout(() => {
      // 移除 resize 事件监听
      resizeHandlers.forEach(h => window.removeEventListener('resize', h))
      resizeHandlers.length = 0
      // 销毁图表实例
      if (klineChart) { klineChart.dispose(); klineChart = null }
      if (macdChart) { macdChart.dispose(); macdChart = null }
      if (kdjChart) { kdjChart.dispose(); kdjChart = null }
    }, 100)
  }
})

// 自动加载
onMounted(() => {
  fetchStocks()
})

// 组件卸载时清理
onUnmounted(() => {
  resizeHandlers.forEach(h => window.removeEventListener('resize', h))
  resizeHandlers.length = 0
  if (klineChart) klineChart.dispose()
  if (macdChart) macdChart.dispose()
  if (kdjChart) kdjChart.dispose()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.app-header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
  max-width: 1400px;
  margin: 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon { font-size: 28px; }

.app-title {
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-content {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.stats-row {
  margin-bottom: 16px;
}

.stats-row .ant-col {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:hover {
  background-color: #e6f7ff !important;
}

.ant-table-wrapper {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.ant-card-head {
  border-bottom: 1px solid #f0f0f0;
}
</style>