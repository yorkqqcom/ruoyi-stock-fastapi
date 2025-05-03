<template>
  <div class="app-container" @keydown.enter="handleEnterKey">
    <!-- 查询条件 -->
    <el-form :inline="true">
      <el-form-item label="股票代码">
        <el-input
          v-model="queryForm.symbol"
          ref="symbolInput"
          :placeholder="lastSymbol || '如：600000'"
          class="light-input"
          style="width: 200px"
        />
      </el-form-item>

      <el-form-item label="复权类型">
        <el-select
          v-model="queryForm.adjustType"
          class="light-select"
        >
          <el-option label="前复权" value="qfq"/>
          <el-option label="后复权" value="hfq"/>
          <el-option label="不复权" value="normal"/>
        </el-select>
      </el-form-item>

      <el-form-item label="日期范围">
        <el-date-picker
          v-model="queryForm.dateRange"
          type="daterange"
          class="light-date-picker"
          value-format="yyyy-MM-dd"
          range-separator="至"
        />
      </el-form-item>

      <el-button
        type="primary"
        @click="loadData"
        :loading="loading"
        icon="el-icon-search"
        style="background: #409EFF;"
      >
        查询
      </el-button>
      <el-button
        type="warning"
        @click="handleAnalyze"
        :loading="analyzeLoading"
        icon="el-icon-data-analysis"
        style="margin-left: 15px;"
      >
        智能分析
      </el-button>
    </el-form>

    <!-- ECharts容器 -->
    <div ref="chart" class="chart-container"></div>

    <!-- 新增指标展示区域 -->
    <el-card class="analysis-card" v-if="analysisData">
      <div slot="header" class="clearfix">
        <span>训练样本数据情况</span>
      </div>

      <!-- 基础指标 -->
      <el-descriptions title="样本数据基础统计" :column="4" border>
        <el-descriptions-item label="训练数据行数">
          {{ analysisData.stats.train_data_rows || 0 }}天
        </el-descriptions-item>
        <el-descriptions-item label="成交量高于5日均线">
          {{ analysisData.stats.volume_above_ma5 || 0 }}天
        </el-descriptions-item>
        <el-descriptions-item label="价格高于20日均线">
          {{ analysisData.stats.price_above_ma20 || 0 }}天
        </el-descriptions-item>
        <el-descriptions-item label="低波动率天数">
          {{ analysisData.stats.low_volatility || 0 }}天
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
    <el-card class="analysis-card" v-if="analysisData">
      <div slot="header" class="clearfix">
        <span>历史回测指标</span>
      </div>
      <el-descriptions
        v-for="period in [5, 10, 20]"
        :key="period"
        :title="period + '日回测周期'"
        :column="6"
        border
      >
        <el-descriptions-item label="平均收益">
          {{ formatPercentage(analysisData.performance[`avg_return_${period}_day`]) }}
        </el-descriptions-item>
        <el-descriptions-item label="年化收益率">
          {{ formatPercentage(analysisData.performance[`annualized_return_${period}_day`]) }}
        </el-descriptions-item>
        <el-descriptions-item label="胜率">
           <span :style="getWinRateStyle(analysisData.performance[`win_rate2_${period}_day`])">
              {{ formatPercentage(analysisData.performance[`win_rate2_${period}_day`]) }}
           </span>
        </el-descriptions-item>
        <el-descriptions-item label="年化波动率">
          {{ formatPercentage(analysisData.performance[`volatility_${period}_day`]) }}
        </el-descriptions-item>
        <el-descriptions-item label="最大回撤">
          {{ formatPercentage(analysisData.performance[`max_drawdown_${period}_day`]) }}
        </el-descriptions-item>
        <el-descriptions-item label="夏普比率">
          {{ formatPercentage(analysisData.performance[`sharpe_ratio_${period}_day`])}}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>
<!-- 在分析卡片之后添加提示 -->
<el-alert
  v-if="analysisData && signalsData.length === 0"
  type="info"
  title="无买卖信号"
  description="当前分析周期内未检测到有效的买入或卖出信号"
  show-icon
  :closable="false"
  style="margin-top: 20px;"
/>
<script>
import * as echarts from 'echarts'
import { getKline, getanalyzer } from '@/api/stock/kline'

function calculateMA(data, window) {
  return data.map((d, index) => {
    if (index < window - 1) return null
    const sum = data
      .slice(index - window + 1, index + 1)
      .reduce((a, b) => a + b.close, 0)
    return Number((sum / window).toFixed(2))
  })
}

export default {
  data() {
    const end = new Date()
    const start = new Date()
    start.setMonth(start.getMonth() - 12 )

    return {
      analysisData: null, // 改为响应式属性
      analyzeLoading: false,
      signalsData: [],
      lastSymbol: '',
      loading: false,
      queryForm: {
        symbol: '600519',
        adjustType: 'qfq',
        dateRange: [
          this.formatDate(start),
          this.formatDate(end)
        ]
      },
      chartInstance: null,
      rawData: [], // 新增原始数据存储
      baseMetrics: [
        {
          label: '训练数据',
          key: 'train_data_rows',
          unit: '天',
          tip: '用于模型训练的有效数据量'
        },
        {
          label: '放量天数',
          key: 'volume_above_ma5',
          unit: '天',
          tip: '成交量突破5日均线的交易日数量'
        },
        {
          label: '均线突破',
          key: 'price_above_ma20',
          unit: '天',
          tip: '收盘价位于20日均线上方的交易日'
        },
        {
          label: '低波动天数',
          key: 'low_volatility',
          unit: '天',
          tip: '日内波动率小于2%的交易日'
        }
      ],
      periodMetrics: [
        {
          label: '年化收益',
          key: 'annualized_return',
          type: 'percentage',
          precision: 1,
          tip: '折算为年收益率的投资回报'
        },
        {
          label: '胜率',
          key: 'win_rate2',
          type: 'percentage',
          precision: 0,
          tip: '获得正收益的交易日占比'
        },
        {
          label: '波动率',
          key: 'volatility',
          type: 'percentage',
          precision: 1,
          tip: '收益率的标准差，衡量风险水平'
        },
        {
          label: '最大回撤',
          key: 'max_drawdown',
          type: 'percentage',
          precision: 1,
          reverse: true,
          tip: '期间最大亏损幅度'
        },
        {
          label: '夏普比率',
          key: 'sharpe_ratio',
          type: 'number',
          precision: 2,
          tip: '衡量风险调整后的收益'
        }
      ]
    }
  },

  mounted() {
    this.initChart()
    this.loadData()
    window.addEventListener('resize', this.handleResize)
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
    if (this.chartInstance) {
      this.chartInstance.dispose()
    }
  },

  methods: {
    // 初始化图表
    initChart() {
      this.chartInstance = echarts.init(this.$refs.chart)
      const option = {
        backgroundColor: '#fff',
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(255,255,255,0.9)',
          borderWidth: 1,
          borderColor: '#ccc',
          textStyle: { color: '#333' },
          formatter: params => {
            const kData = params.find(item => item.seriesType === 'candlestick')
            const ma5 = params.find(item => item.seriesName === 'MA5')
            const ma10 = params.find(item => item.seriesName === 'MA10')
            if (!kData) return ''

            const data = this.rawData[kData.dataIndex]
            return `
              ${data.date}<br/>
              开: ${data.open.toFixed(2)}<br/>
              收: ${data.close.toFixed(2)}<br/>
              低: ${data.low.toFixed(2)}<br/>
              高: ${data.high.toFixed(2)}<br/>
              量: ${data.volume.toLocaleString()}<br/>
              ${ma5?.value ? `MA5: ${ma5.value.toFixed(2)}<br/>` : ''}
              ${ma10?.value ? `MA10: ${ma10.value.toFixed(2)}` : ''}
            `
          }
        },
        legend: {
          data: ['K线', '成交量', 'MA5', 'MA10'],
          textStyle: { color: '#666' },
          itemGap: 20
        },
        grid: [
          { left: '10%', right: '8%', height: '60%', top: '10%' },
          { left: '10%', right: '8%', top: '72%', height: '15%' }
        ],
        xAxis: [
          {
            type: 'category',
            boundaryGap: false,
            axisLine: { lineStyle: { color: '#dcdfe6' } },
            axisLabel: { color: '#666', formatter: value => value.split(' ')[0] },
            splitLine: { show: false }
          },
          {
            type: 'category',
            gridIndex: 1,
            axisLine: { lineStyle: { color: '#dcdfe6' } },
            axisLabel: { show: false },
            splitLine: { show: false }
          }
        ],
        yAxis: [
          {
            scale: true,
            splitNumber: 2,
            axisLine: { lineStyle: { color: '#dcdfe6' } },
            axisLabel: { color: '#666' },
            splitLine: { lineStyle: { type: 'dashed', color: '#eee' } }
          },
          {
            scale: true,
            gridIndex: 1,
            splitNumber: 2,
            axisLine: { show: false },
            axisLabel: { show: false },
            splitLine: { show: false }
          }
        ],
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0, 1],
            start: 0,
            end: 100,
            minValueSpan: 30
          },
          {
            type: 'slider',
            xAxisIndex: [0, 1],
            bottom: 20,
            height: 18,
            handleStyle: { color: '#999' },
            fillerColor: 'rgba(153,153,153,0.1)'
          }
        ],
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            itemStyle: {
              color: '#ef5350',
              color0: '#26a69a',
              borderColor: '#ef5350',
              borderColor0: '#26a69a'
            },
            data: []
          },
          {
            name: '成交量',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            itemStyle: {
              color: params => {
                const data = this.rawData[params.dataIndex]
                return data.close > data.open ? '#26a69a' : '#ef5350'
              }
            },
            data: []
          },
          {
            name: 'MA5',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#ff9800' },
            data: []
          },
          {
            name: 'MA10',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#2196f3' },
            data: []
          }
        ]
      }
      this.chartInstance.setOption(option)
    },

    // 加载数据 在loadData方法中
    async loadData() {
      const currentSymbol = this.queryForm.symbol.trim()
      if (!/^\d{6}$/.test(currentSymbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return
      }

      this.loading = true
      try {
        const { data } = await getKline(this.queryForm)
        this.rawData = data.sort((a, b) => new Date(a.date) - new Date(b.date))
        this.lastSymbol = currentSymbol

        const dates = this.rawData.map(d => d.date)
        const kData = this.rawData.map(d => [d.open, d.close, d.low, d.high])
        const volumes = this.rawData.map(d => d.volume)
        const ma5 = calculateMA(this.rawData, 5)
        const ma10 = calculateMA(this.rawData, 10)

        this.chartInstance.setOption({
          xAxis: [{ data: dates }, { data: dates }],
          series: [
            { data: kData },
            { data: volumes },
            { data: ma5 },
            { data: ma10 }
          ]
        })
      } catch (error) {
        this.$message.error('数据加载失败')
      } finally {
        this.loading = false
      }
    },


    handleResize() {
      this.chartInstance.resize()
    },

    formatDate(date) {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },
    handleKeyDown(event) {
      // 如果焦点在输入元素内，则不处理
      const activeElement = document.activeElement;
      const isInput = activeElement.tagName === 'INPUT' || activeElement.tagName === 'SELECT' || activeElement.tagName === 'TEXTAREA';
      if (isInput) {
        return;
      }

      const key = event.key;

      // 处理数字键
      if (key >= '0' && key <= '9') {
        event.preventDefault();
        this.queryForm.symbol += key;
      }

      // 处理退格键（可选）
      if (key === 'Backspace') {
        event.preventDefault();
        this.queryForm.symbol = this.queryForm.symbol.slice(0, -1);
      }

      // 处理回车键
      if (key === 'Enter') {
        event.preventDefault();
        if (this.queryForm.symbol) {
          this.loadData();
        }
      }
    },
    formatPercentage(value) {
      if (typeof value !== 'number') return '-'
      return `${(value * 100).toFixed(2)}%`
    },
    handleEnterKey(event) {
      // 排除以下情况：
      // 1. 正在输入其他表单元素
      // 2. 没有输入股票代码
      // 3. 正在加载中
      if (
        event.target.tagName === 'INPUT' ||
        event.target.tagName === 'TEXTAREA' ||
        !this.queryForm.symbol ||
        this.loading
      ) return

      this.loadData()
    },
    async handleAnalyze() {
      if (!this.lastSymbol) {
        this.$message.warning('请先查询股票数据')
        return
      }

      this.analyzeLoading = true
      try {
        const { data } = await getanalyzer({
          symbol: this.lastSymbol,
          start_date: this.queryForm.dateRange[0],
          end_date: this.queryForm.dateRange[1]
        })
        // 添加信号数据校验
        if (!data.signals || data.signals.length === 0) {
          this.$message.info('当前分析结果未发现交易信号')
        }
        // 保存分析数据
        this.analysisData = {
          stats: data.stats,
          performance: data.performance
        }

        this.signalsData = data.signals

        this.signalsData = data.signals || []  // 确保总是数组
        this.updateChartWithSignals()
      } catch (error) {
        this.$message.error('分析失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.analyzeLoading = false
      }
    },

    updateChartWithSignals() {

      // 生成标记点数据
      const markPoints = this.signalsData.map(signal => {
        // 兼容带时间戳的日期格式（去除时间部分）
        const signalDate = signal.date.split(' ')[0]
        const index = this.rawData.findIndex(d => {
          const dataDate = new Date(d.date).toISOString().split('T')[0]
          return dataDate === signalDate
        })

        if (index === -1) return null

        return {
          name: `${signal.type}-${signalDate}`,
          coord: [index, signal.type === 'BUY'
            ? this.rawData[index].low * 0.98
            : this.rawData[index].high * 1.02],
          value: signal.type,
          symbol: 'triangle',
          symbolSize: [28, 28],
          symbolOffset: [0, signal.type === 'BUY' ? -10 : 10],
          symbolRotate: signal.type === 'SELL' ? 180 : 0,
          itemStyle: {
            color: signal.type === 'BUY' ? '#ef5350' : '#26a69a',
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            position: 'insideBottom',
            color: '#fff',
            formatter: signal.type === 'BUY' ? '买' : '卖',
            fontSize: 12,
            fontWeight: 'bold'
          }
        }
      }).filter(Boolean)

      // 安全更新图表配置（保留现有数据）
      this.chartInstance.setOption({
        series: [
          {
            // 对应K线系列的索引
            type: 'candlestick',
            markPoint: {
              data: markPoints,
              animation: true,
              symbolSize: 28,
              label: {
                fontSize: 14,
                fontWeight: 'bold'
              }
            }
          }
        ]
      }, { notMerge: false })
    },

    // 修改原有键盘处理（移除回车处理）
    handleKeyInput(event) {
      const activeTag = document.activeElement.tagName.toLowerCase()
      if (['input', 'textarea'].includes(activeTag)) return

      if (event.key >= '0' && event.key <= '9') {
        if (this.queryForm.symbol.length < 6) {
          this.queryForm.symbol += event.key
        }
        event.preventDefault()
      }

      if (event.key === 'Backspace') {
        this.queryForm.symbol = this.queryForm.symbol.slice(0, -1)
        event.preventDefault()
      }
    },
    getWinRateStyle(winRate) {
      if (typeof winRate !== 'number') return {}
      if (winRate > 0.6) return { color: '#67C23A', fontWeight: 'bold' }
      if (winRate < 0.5) return { color: '#F56C6C', fontWeight: 'bold' }
      return {}
    }
  }
}
</script>

<style scoped>
/* 在style部分添加 */
.el-button--warning {
  background: #ffba00;
  border-color: #ffba00;
  color: #fff;
}

.el-button--warning:hover {
  background: #ffa200;
  border-color: #ffa200;
}

.signal-marker {
  font-weight: bold;
  text-shadow: 0 0 3px rgba(0,0,0,0.5);
}

.app-container {
  background-color: #fff;
  padding: 20px;
  min-height: 100vh;
}

.chart-container {
  height: 700px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-top: 20px;
}

::v-deep .el-form-item__label {
  color: #606266 !important;
}

::v-deep .light-input .el-input__inner {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
  color: #303133 !important;
}

::v-deep .light-select .el-input__inner {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
  color: #303133 !important;
}

::v-deep .light-date-picker .el-range-input {
  background-color: #fff !important;
  color: #303133 !important;
}

::v-deep .light-date-picker .el-range-separator {
  color: #303133 !important;
}
/* 指标卡片容器样式 */
.analysis-card {
  margin-top: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s;
}

.analysis-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

/* 卡片标题样式 */
.analysis-card ::v-deep .el-card__header {
  background: linear-gradient(120deg, #f8f9fc 0%, #f1f3f8 100%);
  border-bottom: 1px solid #e8e8e8;
}

.analysis-card ::v-deep .el-card__header span {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  letter-spacing: 0.5px;
}

/* 描述列表增强样式 */
.analysis-card ::v-deep .el-descriptions {
  margin: 15px 0;
}

/* 描述项标题样式 */
.analysis-card ::v-deep .el-descriptions-item__label {
  background-color: #f8fafc;
  font-weight: 500;
  color: #5a6d88 !important;
  width: 160px;
  text-align: right;
}

/* 描述项内容样式 */
.analysis-card ::v-deep .el-descriptions-item__content {
  color: #34495e;
  font-weight: 500;
  min-width: 100px;
}

/* 表格边框优化 */
.analysis-card ::v-deep .el-descriptions--border td {
  border-color: #eaeef3 !important;
}

/* 标题分隔线 */
.analysis-card ::v-deep .el-descriptions__title {
  position: relative;
  padding-left: 12px;
  margin: 20px 0 15px;
  font-size: 15px;
  color: #409EFF;
}

.analysis-card ::v-deep .el-descriptions__title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background-color: #409EFF;
  border-radius: 2px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .analysis-card ::v-deep .el-descriptions-item {
    width: 100% !important;
    margin-bottom: 8px;
  }

  .analysis-card ::v-deep .el-descriptions-item__label {
    width: 100px;
    text-align: left !important;
  }
}
</style>
