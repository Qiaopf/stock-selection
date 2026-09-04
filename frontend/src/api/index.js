import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 0  // 不设超时，选股耗时较长，前端可以等
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export function getFilteredStocks(params = {}) {
  return api.get('/stocks', { params })
}

export function getStockDetail(code, name = '') {
  return api.get(`/stock/${code}`, { params: { name } })
}

export function getStockList() {
  return api.get('/stock-list')
}

export function getProgress() {
  return api.get('/stocks/progress')
}

export function getStatus() {
  return api.get('/status')
}

export default api