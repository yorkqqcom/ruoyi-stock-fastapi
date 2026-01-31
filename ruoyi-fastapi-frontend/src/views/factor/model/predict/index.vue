<template>
  <div class="app-container">
    <!-- 查询区 -->
    <el-card class="query-card" shadow="hover">
      <el-form :model="form" ref="queryFormRef" :inline="true" label-width="60px">
        <el-form-item label="股票" prop="stockKeyword">
          <el-autocomplete
            v-model="form.stockKeyword"
            :fetch-suggestions="searchStock"
            placeholder="代码 / 中文名 / 英文名"
            style="width: 260px"
            clearable
            @select="handleStockSelect"
          />
        </el-form-item>
        <el-form-item label="模型" prop="resultId">
          <el-select
            v-model="form.resultId"
            placeholder="请选择模型"
            filterable
            clearable
            style="width: 240px"
            @visible-change="(visible) => visible && loadModelOptions()"
          >
            <el-option
              v-for="item in modelOptions"
              :key="item.id"
              :label="item.taskName + ' / v' + (item.version || 1) + '（结果ID：' + item.id + '）'"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            icon="Search"
            :loading="loadingPredict"
            @click="handleQueryPredict"
          >
            获取最新预测
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 结果区 -->
    <el-card class="result-card" shadow="never" v-if="hasSearched">
      <template #header>
        <span>最新预测结果</span>
      </template>

      <div v-if="latestPredict">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="24" :md="10" :lg="8" class="result-info">
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="股票">
                {{ stockDisplay }}
              </el-descriptions-item>
              <el-descriptions-item label="模型">
                {{ currentModelName }}（ID：{{ latestPredict.resultId }}）
              </el-descriptions-item>
              <el-descriptions-item label="交易日期">
                {{ formatTradeDate(latestPredict.tradeDate) }}
              </el-descriptions-item>
              <el-descriptions-item label="预测标签">
                <el-tag v-if="latestPredict.predictLabel === 1" type="success">涨</el-tag>
                <el-tag v-else-if="latestPredict.predictLabel === 0" type="danger">跌</el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="预测概率">
                <span v-if="latestPredict.predictProb != null">
                  {{ (latestPredict.predictProb * 100).toFixed(2) }}%
                </span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="实际标签">
                <el-tag v-if="latestPredict.actualLabel === 1" type="success">涨</el-tag>
                <el-tag v-else-if="latestPredict.actualLabel === 0" type="danger">跌</el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="预测是否正确">
                <el-tag v-if="latestPredict.isCorrect === '1'" type="success">正确</el-tag>
                <el-tag v-else-if="latestPredict.isCorrect === '0'" type="danger">错误</el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="预测时间">
                <span v-if="latestPredict.createTime">
                  {{ parseTime ? parseTime(latestPredict.createTime) : latestPredict.createTime }}
                </span>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>

          <el-col :xs="24" :sm="24" :md="14" :lg="16" class="result-chart">
            <div ref="chartRef" class="predict-chart"></div>
          </el-col>
        </el-row>
      </div>
      <div v-else>
        <el-empty description="尚无该模型对该股票的预测记录" />
      </div>
    </el-card>

    <el-empty
      v-else
      description="请选择股票和模型后点击“获取最新预测”"
    />
  </div>
</template>

<script setup name="ModelPredictResult">
import { listModelPredictResult, listModelTrainResult, predictModel } from '@/api/factor/model'
import { searchStockBasic, getDailyKline } from '@/api/tushare/stock'
import * as echarts from 'echarts'

const { proxy } = getCurrentInstance()

const form = reactive({
  stockKeyword: '',
  tsCode: undefined,
  resultId: undefined
})

const modelOptions = ref([])
const latestPredict = ref(null)
const loadingPredict = ref(false)
const hasSearched = ref(false)
const selectedStock = ref(null)

const chartRef = ref(null)
let chartInstance = null

function loadModelOptions() {
  if (modelOptions.value.length > 0) {
    return
  }
  // 只取成功的训练结果，可按需调整查询条件
  listModelTrainResult({ pageNum: 1, pageSize: 100, status: '0' }).then((res) => {
    const rows = res.rows || []
    modelOptions.value = rows.map((item) => ({
      id: item.id,
      taskId: item.taskId,
      version: item.version,
      taskName: item.taskName
    }))
  })
}

function searchStock(queryString, cb) {
  if (!queryString) {
    cb([])
    return
  }
  searchStockBasic({ keyword: queryString, limit: 20 }).then((res) => {
    const list = res.data || []
    cb(
      list.map((item) => ({
        // 仅用于展示的文本，避免 tsCode 为 null 时出现 "null -"
        value: `${item.tsCode || item.symbol || ''}${item.name ? ` - ${item.name}` : ''}${
          item.symbol ? ` (${item.symbol})` : ''
        }`,
        tsCode: item.tsCode,
        name: item.name,
        symbol: item.symbol
      }))
    )
  })
}

function handleStockSelect(item) {
  form.tsCode = item.tsCode
  selectedStock.value = item
}

const stockDisplay = computed(() => {
  if (selectedStock.value) {
    const { tsCode, name, symbol } = selectedStock.value
    const codePart = tsCode || symbol || ''
    const namePart = name || ''
    const main = [codePart, namePart].filter(Boolean).join(' - ')
    return main || symbol || '-'
  }
  if (latestPredict.value?.tsCode) {
    return latestPredict.value.tsCode
  }
  return '-'
})

const currentModelName = computed(() => {
  if (!latestPredict.value) return '-'
  const match = modelOptions.value.find((item) => item.id === latestPredict.value.resultId)
  if (!match) return '未知模型'
  const v = match.version || 1
  return `${match.taskName} / v${v}`
})

function formatTradeDate(val) {
  if (!val) return '-'
  const s = String(val)
  if (s.length === 8) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  }
  return s
}

function getOffsetDate(yyyymmdd, offsetDays) {
  const s = String(yyyymmdd)
  const year = Number(s.slice(0, 4))
  const month = Number(s.slice(4, 6)) - 1
  const day = Number(s.slice(6, 8))
  const date = new Date(year, month, day)
  date.setDate(date.getDate() + offsetDays)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}${m}${d}`
}

function clearChart() {
  if (chartInstance) {
    chartInstance.clear()
  }
}

// 当用户只输入代码/名称但没有点选下拉时，尝试自动解析成 tsCode
async function ensureTsCodeFromKeyword() {
  if (form.tsCode || !form.stockKeyword) {
    return
  }
  try {
    const res = await searchStockBasic({ keyword: form.stockKeyword, limit: 1 })
    const list = res.data || []
    if (list.length > 0) {
      const item = list[0]
      form.tsCode = item.tsCode
      selectedStock.value = {
        value: `${item.tsCode} - ${item.name || ''} ${item.symbol ? `(${item.symbol})` : ''}`,
        tsCode: item.tsCode,
        name: item.name,
        symbol: item.symbol
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    // 如果通过搜索仍然无法解析，但用户有输入内容，则尝试从输入中提取纯数字代码
    if (!form.tsCode && form.stockKeyword) {
      const trimmed = form.stockKeyword.trim()
      // 尝试提取开头的数字代码（6位或更少，可能是股票代码）
      const codeMatch = trimmed.match(/^(\d{4,6})/)
      if (codeMatch) {
        form.tsCode = codeMatch[1]
      } else {
        // 如果提取不到数字，尝试提取括号内的代码，如 "(301428)"
        const parenMatch = trimmed.match(/\((\d{4,6})\)/)
        if (parenMatch) {
          form.tsCode = parenMatch[1]
        } else {
          // 最后兜底：直接使用去除空格后的值
          form.tsCode = trimmed
        }
      }
    }
  }
}

function renderChart(priceRows) {
  if (!chartRef.value || !priceRows || priceRows.length === 0 || !latestPredict.value) {
    clearChart()
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value, 'macarons')
  }

  const dates = priceRows.map((item) => item.tradeDate ?? item.trade_date)
  const closes = priceRows.map((item) => item.close)

  const predictDate = latestPredict.value.tradeDate ?? latestPredict.value.trade_date
  const idx = dates.indexOf(predictDate)
  const signalPoints =
    idx !== -1
      ? [
          {
            value: [dates[idx], closes[idx]],
            name: '预测信号',
            tradeDate: dates[idx]
          }
        ]
      : []

  const isUp = latestPredict.value.predictLabel === 1

  const option = {
    grid: {
      left: 40,
      right: 20,
      top: 40,
      bottom: 40
    },
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const items = Array.isArray(params) ? params : [params]
        const xLabel = items[0]?.axisValue || ''
        const priceItem = items.find((p) => p.seriesName === '收盘价')
        const price = priceItem ? priceItem.data : '-'
        const label =
          latestPredict.value.predictLabel === 1
            ? '涨'
            : latestPredict.value.predictLabel === 0
              ? '跌'
              : '-'
        const prob =
          latestPredict.value.predictProb != null
            ? `${(latestPredict.value.predictProb * 100).toFixed(2)}%`
            : '-'
        return [
          `日期：${formatTradeDate(xLabel)}`,
          `收盘价：${price}`,
          `预测：${label}`,
          `概率：${prob}`
        ].join('<br/>')
      }
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    dataZoom: [
      { type: 'inside', start: 40, end: 100 },
      { type: 'slider', start: 40, end: 100 }
    ],
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: closes,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2
        }
      },
      {
        name: '预测信号',
        type: 'scatter',
        data: signalPoints,
        symbolSize: 12,
        itemStyle: {
          color: isUp ? '#67C23A' : '#F56C6C'
        },
        z: 10
      }
    ]
  }

  chartInstance.setOption(option, true)
}

async function loadKlineAndRenderChart() {
  if (!latestPredict.value) {
    clearChart()
    return
  }

  const tradeDate = latestPredict.value.tradeDate
  const endDate = tradeDate
  const startDate = getOffsetDate(tradeDate, -90)

  try {
    const normalizedCode = normalizeTsCode(form.tsCode)
    const res = await getDailyKline({
      tsCode: normalizedCode,
      startDate,
      endDate
    })
    const rows = res.data || []
    renderChart(rows)
  } catch (error) {
    console.error(error)
    clearChart()
  }
}

// 根据代码前缀自动补全 Tushare 标准后缀
function normalizeTsCode(code) {
  if (!code) return code
  // 如果已经有后缀，直接返回
  if (code.includes('.')) {
    return code
  }
  // 根据代码前缀判断市场
  const prefix = code.substring(0, 1)
  if (prefix === '6' || prefix === '9') {
    return `${code}.SH` // 上海
  } else if (prefix === '0' || prefix === '3') {
    return `${code}.SZ` // 深圳
  } else if (prefix === '4' || prefix === '8') {
    return `${code}.BJ` // 北京
  } else if (code.length <= 5 && /^\d+$/.test(code)) {
    return `${code}.HK` // 香港（5位数字）
  }
  // 无法判断时，返回原值（后端会用 LIKE 匹配）
  return code
}

// 从日线数据中获取该股票最近一个有价格记录的交易日
async function getLatestTradeDateForTsCode() {
  const normalizedCode = normalizeTsCode(form.tsCode)
  console.log('[日线] 请求参数:', { tsCode: normalizedCode, formTsCode: form.tsCode })

  try {
    const res = await getDailyKline({
      tsCode: normalizedCode
    })

    // ========== 详细日志：响应结构 ==========
    console.log('[日线] 响应整体:', {
      resKeys: res ? Object.keys(res) : null,
      resCode: res?.code,
      resMsg: res?.msg,
      hasData: res?.data !== undefined,
      dataIsArray: Array.isArray(res?.data),
      dataLength: Array.isArray(res?.data) ? res.data.length : '-'
    })

    const rows = res?.data || []
    if (!rows.length) {
      console.warn('[日线] 无数据: rows 为空或长度为 0')
      return null
    }

    // ========== 详细日志：第一条和最后一条 ==========
    const first = rows[0]
    const last = rows[rows.length - 1]
    console.log('[日线] 第一条记录:', {
      keys: Object.keys(first),
      tradeDate: first.tradeDate,
      trade_date: first.trade_date,
      tsCode: first.tsCode,
      ts_code: first.ts_code,
      raw: first
    })
    console.log('[日线] 最后一条记录:', {
      keys: Object.keys(last),
      tradeDate: last.tradeDate,
      trade_date: last.trade_date,
      tsCode: last.tsCode,
      ts_code: last.ts_code,
      raw: last
    })

    const tradeDate = last.tradeDate ?? last.trade_date
    console.log('[日线] 解析出的最新交易日:', tradeDate, tradeDate ? '✓' : '✗ 为 undefined/null')
    return tradeDate
  } catch (e) {
    console.error('[日线] 请求异常:', e)
    console.error('[日线] 异常详情:', {
      message: e?.message,
      response: e?.response,
      responseData: e?.response?.data,
      code: e?.response?.data?.code,
      msg: e?.response?.data?.msg
    })
    const code = e?.response?.data?.code
    if (code === 401 || code === 403) {
      throw e
    }
    return null
  }
}

async function handleQueryPredict() {
  // 先根据用户输入尝试解析股票代码，避免只输入未点选时 tsCode 为空
  await ensureTsCodeFromKeyword()
  if (!form.tsCode) {
    proxy.$modal.msgWarning('请先选择股票或输入有效的股票代码')
    return
  }
  if (!form.resultId) {
    proxy.$modal.msgWarning('请先选择模型')
    return
  }

  loadingPredict.value = true
  hasSearched.value = true

  try {
    // 1. 确定用于预测的交易日期：取该股票最新一个有价格数据的交易日
    const normalizedCode = normalizeTsCode(form.tsCode)
    console.log('[预测] 开始获取最新交易日, normalizedCode:', normalizedCode)
    const latestTradeDate = await getLatestTradeDateForTsCode()
    console.log('[预测] getLatestTradeDateForTsCode 返回:', latestTradeDate, typeof latestTradeDate)
    if (!latestTradeDate) {
      console.warn('[预测] 最新交易日为空，将提示「未找到日线数据」')
      latestPredict.value = null
      clearChart()
      proxy.$modal.msgWarning(`未找到股票 ${normalizedCode} 的日线数据，无法执行预测。请先在「数据下载」中下载该股票的行情数据后再试。`)
      return
    }

    // 2. 先执行一次实时预测（根据最新交易日）
    const predictRes = await predictModel({
      resultId: form.resultId,
      tsCodes: normalizedCode,
      tradeDate: latestTradeDate
    })
    
    // 检查预测接口返回结果（根据 success 字段或 code 字段判断）
    if (predictRes.success === false || (predictRes.code && predictRes.code !== 200)) {
      const errorMsg = predictRes.msg || '预测执行失败，请检查该股票是否有因子数据'
      latestPredict.value = null
      clearChart()
      proxy.$modal.msgError(errorMsg)
      return
    }

    // 3. 再查询该模型+股票的最新一条预测结果
    const res = await listModelPredictResult({
      resultId: form.resultId,
      tsCode: normalizedCode,
      pageNum: 1,
      pageSize: 1
    })
    const rows = res.rows || []
    if (!rows.length) {
      latestPredict.value = null
      clearChart()
      proxy.$modal.msgWarning('预测已执行，但未查询到预测结果，请稍后重试')
      return
    }
    latestPredict.value = rows[0]
    await loadKlineAndRenderChart()
    proxy.$modal.msgSuccess('预测完成')
  } catch (error) {
    console.error(error)
    latestPredict.value = null
    clearChart()
    const errorMsg = error?.response?.data?.msg || error?.message || '预测执行失败，请检查网络连接或联系管理员'
    proxy.$modal.msgError(errorMsg)
  } finally {
    loadingPredict.value = false
  }
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}

.query-card {
  margin-bottom: 20px;
}

.result-card {
  margin-top: 0;
}

.result-info {
  margin-bottom: 20px;
}

.result-chart {
  height: 420px;
}

.predict-chart {
  width: 100%;
  height: 100%;
}
</style>
