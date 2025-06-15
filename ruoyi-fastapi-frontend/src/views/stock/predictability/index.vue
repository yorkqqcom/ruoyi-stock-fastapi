<template>
  <div class="app-container">
    <!-- 查询条件 -->
    <el-form :inline="true">
      <el-form-item label="股票代码" prop="symbol">
        <el-autocomplete
          v-model="queryForm.symbol"
          :fetch-suggestions="fetchSuggestions"
          placeholder="输入股票代码或名称"
          class="light-input"
          style="width: 200px"
          @select="handleSelectSymbol"
          value-key="symbol"
          :trigger-on-focus="false"
          @input="handleSymbolInput"
        >
          <template slot-scope="{ item }">
            <div class="symbol-item">
              <span class="symbol-code">{{ item.symbol }}</span>
              <span class="symbol-name">{{ item.name }}</span>
            </div>
          </template>
        </el-autocomplete>
      </el-form-item>

      <el-form-item label="日期范围">
        <el-date-picker
          v-model="queryForm.dateRange"
          type="daterange"
          class="light-date-picker"
          value-format="yyyyMMdd"
          range-separator="至"
          :default-time="['00:00:00', '23:59:59']"
        />
      </el-form-item>

      <el-button
        type="primary"
        @click="loadData"
        :loading="loading"
        icon="el-icon-search"
      >
        分析
      </el-button>
    </el-form>

    <!-- 加载提示 -->
    <el-alert
      v-if="loading"
      title="数据加载中..."
      type="info"
      :closable="false"
      show-icon
      class="loading-alert"
    />

    <!-- 市场状态卡片 -->
    <el-card v-if="analysisData" class="market-state-card">
      <div slot="header" class="clearfix">
        <span>市场状态分析</span>
      </div>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="state-item" :class="getStateClass('momentum')">
            <div class="state-title">动量特征</div>
            <div class="state-value">{{ formatPercentage(analysisData.market_state.momentum_ratio) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="state-item" :class="getStateClass('reversion')">
            <div class="state-title">均值回归特征</div>
            <div class="state-value">{{ formatPercentage(analysisData.market_state.reversion_ratio) }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="state-item" :class="getStateClass('random')">
            <div class="state-title">随机特征</div>
            <div class="state-value">{{ formatPercentage(analysisData.market_state.random_ratio) }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 预测信息提示卡片 -->
    <el-card v-if="analysisData" class="prediction-card">
      <div slot="header" class="clearfix">
        <span>市场预测区域探秘</span>
      </div>
      <div class="prediction-content">
        <div class="prediction-section">
          <h4>市场特征解读</h4>
          <p>{{ getMarketStateInterpretation() }}</p>
        </div>
        <div class="prediction-section">
          <h4>技术指标分析</h4>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="indicator-box">
                <h5>方差比率分析</h5>
                <p>{{ getVrAnalysis() }}</p>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="indicator-box">
                <h5>自相关分析</h5>
                <p>{{ getAcorrAnalysis() }}</p>
              </div>
            </el-col>
          </el-row>
        </div>
        <div class="prediction-section">
          <h4>投资策略建议</h4>
          <p>{{ getInvestmentStrategy() }}</p>
        </div>
        <div class="prediction-section">
          <h4>风险提示</h4>
          <p>{{ getRiskWarning() }}</p>
        </div>
      </div>
    </el-card>

    <!-- 图表区域 -->
    <div v-if="analysisData" class="chart-container">
      <div ref="priceChart" class="chart"></div>
      <div ref="vrChart" class="chart"></div>
      <div ref="acorrChart" class="chart"></div>
    </div>

    <!-- 详细指标卡片 -->
    <el-card v-if="analysisData" class="metrics-card">
      <div slot="header" class="clearfix">
        <span>详细指标</span>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="方差比率" name="vr">
          <el-table :data="vrTableData" border style="width: 100%">
            <el-table-column prop="period" label="周期" width="120" />
            <el-table-column prop="value" label="方差比率" width="120">
              <template slot-scope="scope">
                <span :class="getVrClass(scope.row.value)">{{ scope.row.value != null ? scope.row.value.toFixed(3) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="pvalue" label="P值" width="120">
              <template slot-scope="scope">
                <span :class="getPValueClass(scope.row.pvalue)">{{ scope.row.pvalue != null ? scope.row.pvalue.toFixed(3) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="interpretation" label="解释" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="自相关" name="acorr">
          <el-table :data="acorrTableData" border style="width: 100%">
            <el-table-column prop="timeframe" label="时间尺度" width="120" />
            <el-table-column prop="value" label="自相关值" width="120">
              <template slot-scope="scope">
                <span :class="getAcorrClass(scope.row.value, scope.row.threshold)">
                  {{ scope.row.value != null ? scope.row.value.toFixed(3) : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="threshold" label="阈值" width="120">
              <template slot-scope="scope">
                {{ scope.row.threshold != null ? scope.row.threshold.toFixed(3) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="interpretation" label="解释" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 均值回归分析卡片 -->
    <el-card class="box-card">
      <div slot="header" class="clearfix">
        <span>均值回归分析</span>
      </div>
      <el-table :data="meanReversionData" style="width: 100%">
        <el-table-column prop="date" label="日期" width="120"></el-table-column>
        <el-table-column prop="signal" label="信号" width="80">
          <template slot-scope="scope">
            <el-tag :type="scope.row.signal === 'buy' ? 'success' : 'danger'">
              {{ scope.row.signal === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="buy_price" label="买入价格" width="100">
          <template slot-scope="scope">
            {{ scope.row.buy_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="sell_price" label="卖出价格" width="100">
          <template slot-scope="scope">
            {{ scope.row.sell_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="expected_return" label="预期收益" width="100">
          <template slot-scope="scope">
            {{ scope.row.expected_return.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="return_rate" label="收益率" width="100">
          <template slot-scope="scope">
            <span :class="scope.row.return_rate >= 0 ? 'profit' : 'loss'">
              {{ scope.row.return_rate.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getPredictability, getstocklist } from '@/api/stock/kline'

export default {
  name: 'MarketPredictability',
  data() {
    const endDate = new Date()
    const startDate = new Date()
    startDate.setFullYear(endDate.getFullYear() - 3)
    
    return {
      queryForm: {
        symbol: '600519',
        dateRange: [
          this.getDateString(startDate),
          this.getDateString(endDate)
        ]
      },
      loading: false,
      analysisData: null,
      mockSymbols: [],
      activeTab: 'vr',
      charts: {
        price: null,
        vr: null,
        acorr: null
      },
      meanReversionData: []
    }
  },
  computed: {
    vrTableData() {
      if (!this.analysisData) return []
      const latestMetrics = this.analysisData.market_state.latest_metrics
      return Object.entries(latestMetrics.variance_ratio).map(([period, value]) => ({
        period: `${period.split('_')[1]}日`,
        value: value,
        pvalue: latestMetrics.p_values[`PVal_${period.split('_')[1]}`],
        interpretation: this.getVrInterpretation(value, latestMetrics.p_values[`PVal_${period.split('_')[1]}`])
      }))
    },
    acorrTableData() {
      if (!this.analysisData || !this.analysisData.market_state || !this.analysisData.market_state.latest_metrics) return []
      
      const latestMetrics = this.analysisData.market_state.latest_metrics
      const thresholds = this.analysisData.autocorrelation?.thresholds || {}
      
      return Object.entries(latestMetrics.autocorrelation || {}).map(([timeframe, value]) => ({
        timeframe: this.getTimeframeLabel(timeframe),
        value: value != null ? value : null,
        threshold: thresholds[timeframe] != null ? thresholds[timeframe] : null,
        interpretation: this.getAcorrInterpretation(value, thresholds[timeframe])
      }))
    }
  },
  mounted() {
    this.loadStockList()
    this.getMeanReversionAnalysis()
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
    Object.values(this.charts).forEach(chart => {
      if (chart) chart.dispose()
    })
  },
  methods: {
    getDateString(date) {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}${month}${day}`
    },
    async loadStockList() {
      try {
        const response = await getstocklist()
        this.mockSymbols = response.data || []
      } catch (error) {
        console.error('股票列表加载失败:', error)
        this.$message.error('股票列表加载失败')
      }
    },
    fetchSuggestions(queryString, cb) {
      const results = queryString
        ? this.mockSymbols.filter(item => {
            const symbol = String(item.symbol || '')
            const name = String(item.name || '')
            return (
              symbol.toLowerCase().includes(queryString.toLowerCase()) ||
              name.toLowerCase().includes(queryString.toLowerCase())
            )
          })
        : this.mockSymbols
      cb(results)
    },
    handleSelectSymbol(item) {
      this.queryForm.symbol = item.symbol
      this.loadData()
    },
    handleSymbolInput(val) {
      if (val.length > 6) {
        this.queryForm.symbol = val.slice(0, 6)
        return
      }
    },
    async loadData() {
      if (!this.validateSymbol()) return
      
      if (!this.queryForm.dateRange || this.queryForm.dateRange.length !== 2) {
        this.$message.warning('请选择日期范围')
        return
      }
      
      this.loading = true
      try {
        const { data } = await getPredictability({
          symbol: this.queryForm.symbol,
          start_date: this.queryForm.dateRange[0],
          end_date: this.queryForm.dateRange[1]
        })
        this.analysisData = data
        this.$nextTick(() => {
          this.initCharts()
          this.updateCharts()
        })
      } catch (error) {
        console.error('分析失败:', error)
        this.$message.error('分析失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.loading = false
      }
    },
    validateSymbol() {
      if (!/^\d{6}$/.test(this.queryForm.symbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return false
      }
      return true
    },
    initCharts() {
      if (!this.$refs.priceChart || !this.$refs.vrChart || !this.$refs.acorrChart) {
        return
      }
      
      try {
        this.charts.price = echarts.init(this.$refs.priceChart)
        this.charts.vr = echarts.init(this.$refs.vrChart)
        this.charts.acorr = echarts.init(this.$refs.acorrChart)
      } catch (error) {
        console.error('图表初始化失败:', error)
      }
    },
    updateCharts() {
      if (!this.analysisData) return
      
      this.updatePriceChart()
      this.updateVrChart()
      this.updateAcorrChart()
    },
    updatePriceChart() {
      const option = {
        title: {
          text: '股票价格与移动平均线',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: ['收盘价', 'MA200', 'MA7', 'MA30'],
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: this.analysisData.price_data.map(item => item.date)
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '收盘价',
            type: 'line',
            data: this.analysisData.price_data.map(item => item.close)
          },
          {
            name: 'MA200',
            type: 'line',
            data: this.analysisData.price_data.map(item => item.MA200)
          },
          {
            name: 'MA7',
            type: 'line',
            data: this.analysisData.price_data.map(item => item.MA7)
          },
          {
            name: 'MA30',
            type: 'line',
            data: this.analysisData.price_data.map(item => item.MA30)
          }
        ]
      }
      this.charts.price.setOption(option)
    },
    updateVrChart() {
      const option = {
        title: {
          text: '方差比率分析',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: Object.keys(this.analysisData.variance_ratio).map(key => key.replace('VR_', '')),
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: Object.keys(this.analysisData.variance_ratio[Object.keys(this.analysisData.variance_ratio)[0]])
        },
        yAxis: {
          type: 'value',
          scale: true
        },
        series: Object.entries(this.analysisData.variance_ratio).map(([key, data]) => ({
          name: key.replace('VR_', ''),
          type: 'line',
          data: Object.values(data)
        }))
      }
      this.charts.vr.setOption(option)
    },
    updateAcorrChart() {
      const option = {
        title: {
          text: '自相关分析',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: ['日线', '周线', '月线'],
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: Object.keys(this.analysisData.autocorrelation.daily)
        },
        yAxis: {
          type: 'value',
          scale: true
        },
        series: [
          {
            name: '日线',
            type: 'line',
            data: Object.values(this.analysisData.autocorrelation.daily)
          },
          {
            name: '周线',
            type: 'line',
            data: Object.values(this.analysisData.autocorrelation.weekly)
          },
          {
            name: '月线',
            type: 'line',
            data: Object.values(this.analysisData.autocorrelation.monthly)
          }
        ]
      }
      this.charts.acorr.setOption(option)
    },
    handleResize() {
      Object.values(this.charts).forEach(chart => {
        if (chart) chart.resize()
      })
    },
    formatPercentage(value) {
      if (value == null) return '-'
      return `${(value * 100).toFixed(2)}%`
    },
    getStateClass(state) {
      const dominantState = this.analysisData?.market_state.dominant_state
      return {
        'state-item': true,
        'state-dominant': dominantState === state
      }
    },
    getVrClass(value) {
      if (value === null) return ''
      if (value > 1.05) return 'text-success'
      if (value < 0.95) return 'text-danger'
      return 'text-warning'
    },
    getPValueClass(value) {
      if (value === null) return ''
      if (value < 0.05) return 'text-success'
      return 'text-warning'
    },
    getAcorrClass(value, threshold) {
      if (value === null || threshold === null) return ''
      if (Math.abs(value) > threshold) {
        return value > 0 ? 'text-success' : 'text-danger'
      }
      return 'text-warning'
    },
    getVrInterpretation(value, pvalue) {
      if (value === null || pvalue === null) return '数据不足'
      if (pvalue >= 0.05) return '无显著预测性'
      if (value > 1.05) return '存在动量特征'
      if (value < 0.95) return '存在均值回归特征'
      return '接近随机游走'
    },
    getAcorrInterpretation(value, threshold) {
      if (value === null || threshold === null) return '数据不足'
      if (Math.abs(value) <= threshold) return '无显著自相关'
      if (value > threshold) return '存在正自相关（动量）'
      if (value < -threshold) return '存在负自相关（均值回归）'
      return '接近随机游走'
    },
    getTimeframeLabel(timeframe) {
      const labels = {
        daily: '日线',
        weekly: '周线',
        monthly: '月线'
      }
      return labels[timeframe] || timeframe
    },
    getMarketStateInterpretation() {
      if (!this.analysisData) return ''
      
      const state = this.analysisData.market_state
      const dominantState = state.dominant_state
      
      const interpretations = {
        momentum: '当前市场呈现明显的动量特征，价格趋势具有较强的延续性。这种市场环境下，价格倾向于沿着现有趋势继续运行，适合采用趋势跟踪策略。',
        reversion: '当前市场呈现均值回归特征，价格波动倾向于回归到历史平均水平。这种市场环境下，价格偏离均值后往往会向均值方向回归，适合采用反转策略。',
        random: '当前市场呈现随机游走特征，价格变动缺乏明显的规律性。这种市场环境下，历史价格对未来走势的预测能力较弱，建议采用稳健策略。'
      }
      
      return interpretations[dominantState] || '市场特征不明显，建议谨慎观察。'
    },
    
    getVrAnalysis() {
      if (!this.analysisData) return ''
      
      const vr = this.analysisData.market_state.latest_metrics.variance_ratio
      const pvals = this.analysisData.market_state.latest_metrics.p_values
      
      let significantPeriods = []
      let momentumPeriods = []
      let reversionPeriods = []
      
      Object.entries(vr).forEach(([period, value]) => {
        const periodNum = period.split('_')[1]
        const pval = pvals[`PVal_${periodNum}`]
        
        if (pval < 0.05) {
          significantPeriods.push(periodNum)
          if (value > 1.05) {
            momentumPeriods.push(periodNum)
          } else if (value < 0.95) {
            reversionPeriods.push(periodNum)
          }
        }
      })
      
      let analysis = ''
      if (significantPeriods.length > 0) {
        analysis += `在${significantPeriods.join('、')}日周期上发现显著的市场预测性。`
        if (momentumPeriods.length > 0) {
          analysis += `其中${momentumPeriods.join('、')}日周期呈现动量特征，`
        }
        if (reversionPeriods.length > 0) {
          analysis += `${reversionPeriods.join('、')}日周期呈现均值回归特征。`
        }
      } else {
        analysis = '当前各周期均未发现显著的市场预测性。'
      }
      
      return analysis
    },
    
    getAcorrAnalysis() {
      if (!this.analysisData) return ''
      
      const ac = this.analysisData.market_state.latest_metrics.autocorrelation
      const thresholds = this.analysisData.autocorrelation.thresholds
      
      let analysis = []
      
      // 分析日线自相关
      if (Math.abs(ac.daily) > thresholds.daily) {
        analysis.push(`日线呈现${ac.daily > 0 ? '动量' : '均值回归'}特征`)
      }
      
      // 分析周线自相关
      if (Math.abs(ac.weekly) > thresholds.weekly) {
        analysis.push(`周线呈现${ac.weekly > 0 ? '动量' : '均值回归'}特征`)
      }
      
      // 分析月线自相关
      if (Math.abs(ac.monthly) > thresholds.monthly) {
        analysis.push(`月线呈现${ac.monthly > 0 ? '动量' : '均值回归'}特征`)
      }
      
      if (analysis.length > 0) {
        return analysis.join('，') + '。'
      } else {
        return '当前各时间尺度均未发现显著的自相关特征。'
      }
    },
    
    getInvestmentStrategy() {
      if (!this.analysisData) return ''
      
      const state = this.analysisData.market_state
      const dominantState = state.dominant_state
      
      const strategies = {
        momentum: '建议采用趋势跟踪策略：\n1. 可以适当追涨，但要注意设置止损位\n2. 关注成交量配合，在趋势确认时可以考虑加仓\n3. 可以使用移动平均线等趋势指标辅助判断',
        reversion: '建议采用均值回归策略：\n1. 可以在价格显著偏离均值时进行反向操作\n2. 注意控制仓位，分批建仓，避免一次性重仓\n3. 可以使用布林带等波动指标辅助判断',
        random: '建议采用稳健策略：\n1. 以防御为主，可以考虑定投或网格交易策略\n2. 避免追涨杀跌，重点关注基本面\n3. 选择优质标的，分散投资'
      }
      
      return strategies[dominantState] || '建议观望为主，等待更明确的市场信号。'
    },
    
    getRiskWarning() {
      if (!this.analysisData) return ''
      
      const state = this.analysisData.market_state
      const dominantState = state.dominant_state
      
      const warnings = {
        momentum: '注意防范趋势反转风险：\n1. 设置合理的止损位，避免追高\n2. 警惕市场情绪过热，注意风险控制\n3. 关注市场环境变化，及时调整策略',
        reversion: '注意防范均值回归失效风险：\n1. 市场环境可能发生变化，避免过度逆向操作\n2. 控制好仓位，设置合理的止损位\n3. 关注基本面变化，及时调整策略',
        random: '注意防范市场波动风险：\n1. 避免追涨杀跌，控制好仓位\n2. 建议分散投资，不要将资金过度集中在单一标的上\n3. 关注市场环境变化，及时调整策略'
      }
      
      return warnings[dominantState] || '市场风险较大，建议谨慎操作，做好风险控制。'
    },
    async getMeanReversionAnalysis() {
      try {
        const response = await this.$http.get('/api/stock/mean-reversion-analysis')
        if (response.data && response.data.trading_opportunities) {
          this.meanReversionData = response.data.trading_opportunities
        }
      } catch (error) {
        console.error('获取均值回归分析数据失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.app-container {
  padding: 20px;
}

/* 统一股票代码检索样式 */
::v-deep .el-autocomplete {
  width: 200px;
}

::v-deep .el-autocomplete .el-input__inner {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
  color: #303133 !important;
  height: 32px;
  line-height: 32px;
  padding: 0 15px;
  border-radius: 4px;
  transition: border-color .2s cubic-bezier(.645,.045,.355,1);
}

::v-deep .el-autocomplete .el-input__inner:focus {
  border-color: #409EFF !important;
  outline: none;
}

.symbol-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.symbol-item:hover {
  background-color: #f5f7fa;
}

.symbol-code {
  color: #409EFF;
  font-weight: 600;
  margin-right: 15px;
  font-size: 14px;
}

.symbol-name {
  color: #606266;
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 统一表单样式 */
::v-deep .el-form-item__label {
  color: #606266 !important;
  font-size: 14px;
  line-height: 32px;
}

::v-deep .el-form-item {
  margin-bottom: 18px;
  margin-right: 20px;
}

::v-deep .el-form--inline .el-form-item {
  margin-right: 20px;
}

/* 统一按钮样式 */
::v-deep .el-button {
  padding: 9px 20px;
  font-size: 14px;
  border-radius: 4px;
  transition: all .3s;
}

::v-deep .el-button--primary {
  background-color: #409EFF;
  border-color: #409EFF;
}

::v-deep .el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.chart-container {
  margin-top: 20px;
}

.chart {
  height: 400px;
  margin-bottom: 20px;
}

.market-state-card {
  margin-top: 20px;
}

.state-item {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.state-dominant {
  background: #ecf5ff;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.state-title {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
}

.state-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metrics-card {
  margin-top: 20px;
}

.text-success {
  color: #67C23A;
}

.text-warning {
  color: #E6A23C;
}

.text-danger {
  color: #F56C6C;
}

.loading-alert {
  margin: 10px 0;
}

.prediction-card {
  margin-top: 20px;
}

.prediction-content {
  padding: 10px;
}

.prediction-section {
  margin-bottom: 20px;
}

.prediction-section h4 {
  color: #303133;
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: bold;
}

.prediction-section h5 {
  color: #409EFF;
  margin-bottom: 8px;
  font-size: 14px;
}

.prediction-section p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
  text-align: justify;
}

.indicator-box {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  height: 100%;
}

.indicator-box p {
  margin: 0;
  font-size: 13px;
}

.profit {
  color: #67C23A;
}
.loss {
  color: #F56C6C;
}
</style> 