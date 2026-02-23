<template>
  <div class="app-container">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>回测结果详情 - 任务ID: {{ taskId }}</span>
          <el-button type="primary" @click="goBack">返回</el-button>
        </div>
      </template>

      <!-- 绩效指标卡片 -->
      <el-row :gutter="20" class="mb20">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">总收益率</div>
              <div class="metric-value" :class="resultDetail.totalReturn >= 0 ? 'positive' : 'negative'">
                {{ resultDetail.totalReturn ? (resultDetail.totalReturn * 100).toFixed(2) + '%' : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">年化收益率</div>
              <div class="metric-value" :class="resultDetail.annualReturn >= 0 ? 'positive' : 'negative'">
                {{ resultDetail.annualReturn ? (resultDetail.annualReturn * 100).toFixed(2) + '%' : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">最大回撤</div>
              <div class="metric-value negative">
                {{ resultDetail.maxDrawdown ? (resultDetail.maxDrawdown * 100).toFixed(2) + '%' : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">夏普比率</div>
              <div class="metric-value">
                {{ resultDetail.sharpeRatio ? resultDetail.sharpeRatio.toFixed(2) : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="mb20">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">卡玛比率</div>
              <div class="metric-value">
                {{ resultDetail.calmarRatio ? resultDetail.calmarRatio.toFixed(2) : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">胜率</div>
              <div class="metric-value">
                {{ resultDetail.winRate ? (resultDetail.winRate * 100).toFixed(2) + '%' : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">盈亏比</div>
              <div class="metric-value">
                {{ resultDetail.profitLossRatio ? resultDetail.profitLossRatio.toFixed(2) : '-' }}
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="metric-item">
              <div class="metric-label">交易次数</div>
              <div class="metric-value">
                {{ resultDetail.tradeCount || 0 }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 净值曲线图 -->
      <el-card shadow="hover" class="mb20">
        <template #header>
          <span>净值曲线</span>
        </template>
        <div ref="equityChartRef" style="width: 100%; height: 400px"></div>
      </el-card>

      <!-- 交易明细 -->
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <span>交易明细</span>
            <el-form :inline="true" :model="tradeQueryParams">
              <el-form-item label="股票代码">
                <el-input v-model="tradeQueryParams.tsCode" placeholder="请输入股票代码" clearable style="width: 150px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleTradeQuery">查询</el-button>
                <el-button @click="resetTradeQuery">重置</el-button>
              </el-form-item>
            </el-form>
          </div>
        </template>
        <el-table v-loading="tradeLoading" :data="tradeList" border>
          <el-table-column label="交易日期" prop="tradeDate" width="120" align="center" />
          <el-table-column label="股票代码" prop="tsCode" width="120" align="center" />
          <el-table-column label="方向" prop="side" width="80" align="center">
            <template #default="scope">
              <el-tag v-if="scope.row.side === 'buy'" type="success">买入</el-tag>
              <el-tag v-else-if="scope.row.side === 'sell'" type="danger">卖出</el-tag>
              <el-tag v-else>平仓</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" prop="price" width="100" align="right">
            <template #default="scope">
              {{ scope.row.price ? scope.row.price.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="数量" prop="volume" width="100" align="right" />
          <el-table-column label="金额" prop="amount" width="120" align="right">
            <template #default="scope">
              {{ scope.row.amount ? scope.row.amount.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="手续费" prop="fee" width="100" align="right">
            <template #default="scope">
              {{ scope.row.fee ? scope.row.fee.toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="持仓" prop="positionAfter" width="100" align="right" />
          <el-table-column label="总资产" prop="equityAfter" width="120" align="right">
            <template #default="scope">
              {{ scope.row.equityAfter ? scope.row.equityAfter.toFixed(2) : '-' }}
            </template>
          </el-table-column>
        </el-table>
        <pagination
          v-show="tradeTotal > 0"
          :total="tradeTotal"
          v-model:page="tradeQueryParams.pageNum"
          v-model:limit="tradeQueryParams.pageSize"
          @pagination="getTradeList"
        />
      </el-card>
    </el-card>
  </div>
</template>

<script setup name="BacktestResultDetail">
import { getBacktestResultDetail, listBacktestTrade } from '@/api/backtest/index'
import { getCurrentInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'

const { proxy } = getCurrentInstance()
const route = useRoute()
const router = useRouter()

const taskId = computed(() => route.params.taskId)
const loading = ref(true)
const tradeLoading = ref(false)
const resultDetail = ref({})
const tradeList = ref([])
const tradeTotal = ref(0)
const equityChartRef = ref(null)
let equityChart = null

const tradeQueryParams = reactive({
  taskId: undefined,
  tsCode: undefined,
  pageNum: 1,
  pageSize: 20
})

/** 获取结果详情 */
function getResultDetail() {
  if (!taskId.value) return
  loading.value = true
  getBacktestResultDetail(taskId.value).then((response) => {
    resultDetail.value = response.data || {}
    loading.value = false
    // 绘制净值曲线
    nextTick(() => {
      drawEquityChart()
    })
  }).catch(() => {
    loading.value = false
  })
}

/** 绘制净值曲线 */
function drawEquityChart() {
  if (!equityChartRef.value) return

  if (equityChart) {
    equityChart.dispose()
  }

  equityChart = echarts.init(equityChartRef.value)
  const equityCurve = resultDetail.value.equityCurve || []

  const option = {
    title: {
      text: '净值曲线',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        const param = params[0]
        return `${param.name}<br/>净值: ${param.value.toFixed(4)}`
      }
    },
    xAxis: {
      type: 'category',
      data: equityCurve.map(item => item.date),
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: '净值',
      scale: true
    },
    series: [
      {
        name: '净值',
        type: 'line',
        data: equityCurve.map(item => item.nav),
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        lineStyle: {
          color: '#409EFF'
        },
        itemStyle: {
          color: '#409EFF'
        }
      }
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    }
  }

  equityChart.setOption(option)

  // 响应式调整
  window.addEventListener('resize', () => {
    if (equityChart) {
      equityChart.resize()
    }
  })
}

/** 获取交易明细列表 */
function getTradeList() {
  tradeQueryParams.taskId = parseInt(taskId.value, 10)
  if (!tradeQueryParams.taskId) return
  tradeLoading.value = true
  listBacktestTrade(tradeQueryParams).then((response) => {
    tradeList.value = response.rows || []
    tradeTotal.value = response.total || 0
    tradeLoading.value = false
  }).catch(() => {
    tradeLoading.value = false
  })
}

/** 交易明细查询 */
function handleTradeQuery() {
  tradeQueryParams.pageNum = 1
  getTradeList()
}

/** 重置交易明细查询 */
function resetTradeQuery() {
  tradeQueryParams.tsCode = undefined
  handleTradeQuery()
}

/** 返回 */
function goBack() {
  router.back()
}

watch(taskId, () => {
  tradeQueryParams.pageNum = 1
  getResultDetail()
  getTradeList()
}, { immediate: false })

onMounted(() => {
  getResultDetail()
  getTradeList()
})

onUnmounted(() => {
  if (equityChart) {
    equityChart.dispose()
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb20 {
  margin-bottom: 20px;
}

.metric-item {
  text-align: center;
}

.metric-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metric-value.positive {
  color: #67c23a;
}

.metric-value.negative {
  color: #f56c6c;
}
</style>
