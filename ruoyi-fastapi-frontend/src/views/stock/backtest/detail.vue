<template>
  <div class="app-container" @keydown.enter="handleEnterKey">
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

      <el-form-item label="复权类型">
        <el-select
          v-model="queryForm.adjustType"
          class="light-select"
          @change="saveSettings"
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
        买入点分析
      </el-button>
      <el-button
        type="success"
        @click="showAIAnalysis"
        :loading="aiAnalysisLoading"
        icon="el-icon-chat-dot-round"
        style="margin-left: 15px;"
      >
        AI分析报告
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
    <el-alert
      v-if="analysisData && signalsData.length === 0"
      type="info"
      title="无买卖信号"
      description="当前分析周期内未检测到有效的买入或卖出信号"
      show-icon
      :closable="false"
      style="margin-top: 20px;"
    />
    <!-- ECharts容器 -->
    <div ref="chart" class="chart-container"></div>

    <!-- 新增指标展示区域 -->
    <el-card class="analysis-card" v-if="analysisData">
      <div slot="header" class="clearfix">
        <span>训练样本数据情况</span>
      </div>

      <!-- 基础指标 -->
      <el-descriptions title="样本数据基础统计" :column="6" border>
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
        <el-descriptions-item label="上涨天数">
          <span style="color: #67C23A; font-weight: bold;">
            {{ analysisData.stats.up_days || 0 }}天
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="下跌天数">
          <span style="color: #F56C6C; font-weight: bold;">
            {{ analysisData.stats.down_days || 0 }}天
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 新增模型评估指标 -->
      <el-descriptions title="模型评估指标" :column="5" border style="margin-top: 20px;">
        <el-descriptions-item label="AUC-ROC">
          <span :style="getMetricStyle(analysisData.performance.roc_auc)">
            {{ formatPercentage(analysisData.performance.roc_auc) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="精确率">
          <span :style="getMetricStyle(analysisData.performance.precision)">
            {{ formatPercentage(analysisData.performance.precision) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="召回率">
          <span :style="getMetricStyle(analysisData.performance.recall)">
            {{ formatPercentage(analysisData.performance.recall) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="F1分数">
          <span :style="getMetricStyle(analysisData.performance.f1)">
            {{ formatPercentage(analysisData.performance.f1) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="平衡准确率">
          <span :style="getMetricStyle(analysisData.performance.balanced_accuracy)">
            {{ formatPercentage(analysisData.performance.balanced_accuracy) }}
          </span>
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

    <!-- 重点修改AI分析对话框部分 -->
    <el-dialog
      title="AI分析报告"
      :visible.sync="aiAnalysisDialogVisible"
      width="70%"
      :before-close="handleAIAnalysisClose"
      custom-class="ai-analysis-dialog"
    >
      <div v-loading="aiAnalysisLoading" class="ai-dialog-content">
        <!-- 安全渲染HTML内容 -->
        <div v-if="aiAnalysisReport" class="ai-analysis-content">
          <div class="analysis-section">
            <h3>分析报告</h3>
            <!-- 使用v-html指令渲染安全内容 -->
            <div v-html="safeAnalysisReport"></div>
          </div>
        </div>
        <div v-else-if="!aiAnalysisLoading" class="no-analysis">
          暂无AI分析报告
        </div>
      </div>
    </el-dialog>

  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getKline, getanalyzer, getstocklist } from '@/api/stock/kline'
import { postChat } from '@/api/ai/chat'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import DOMPurify from 'dompurify'

// 配置markdown-it
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(lang, str).value
      } catch (__) {}
    }
    return '' // 使用默认的转义
  }
})

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
    // 格式化日期为YYYY-MM-DD
    const formatDate = (date) => {
      return date.toISOString().split('T')[0]
    }
    // 从localStorage获取保存的设置
    let savedSettings = {}

    // 设置默认日期范围
    const defaultDateRange = [
      formatDate(start),
      formatDate(end)
    ]
    return {
      mockSymbols: [],
      analysisData: null,
      analyzeLoading: false,
      signalsData: [],
      loading: false,
      queryForm: {
        symbol: savedSettings.symbol || '600519',
        adjustType: savedSettings.adjustType || 'qfq',
        dateRange: savedSettings.dateRange || defaultDateRange
      },
      chartInstance: null,
      rawData: [],
      debounceTimer: null,
      lastSymbol: '',
      baseMetrics: [],
      periodMetrics: [],
      aiAnalysisDialogVisible: false,
      aiAnalysisLoading: false,
      aiAnalysisReport: null,
      analysisCache: new Map(),
      cacheExpiration: 30 * 60 * 1000,
    }
  },

  created() {
    this.loadStockList();
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
  computed: {
    // 添加安全内容计算属性
    safeAnalysisReport() {
      return DOMPurify.sanitize(this.aiAnalysisReport)
    }
  },
  methods: {

    async loadStockList() {
      try {
        const response = await getstocklist();
        // 根据实际API响应结构调整，确保拿到的是数组
        this.mockSymbols = response.data || [];
      } catch (error) {
        console.error('股票列表加载失败:', error);
        this.$message.error('股票列表加载失败');
      }
    },
    // 新增股票代码选择处理
    handleSelectSymbol(item) {
      this.queryForm.symbol = item.symbol
      this.loadData()
    },

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
    // 自动补全逻辑
    async fetchSuggestions(queryString, cb) {
      try {
        // 确保始终有数组可用
        const source = Array.isArray(this.mockSymbols) ? this.mockSymbols : [];
        const results = source.filter(item => {
          // 确保 item 是对象且具有必要的属性
          if (!item || typeof item !== 'object') return false;
          
          // 确保 symbol 和 name 都是字符串
          const symbol = String(item.symbol || '');
          const name = String(item.name || '');
          
          return symbol.includes(queryString) || name.includes(queryString);
        }).map(item => ({
          ...item,
          value: String(item.symbol || '')
        }));

        cb(results);
      } catch (error) {
        console.error('股票列表过滤出错:', error);
        cb([]);
      }
    },

    // 输入处理
    handleSymbolInput(val) {
      if (val.length > 6) {
        this.queryForm.symbol = val.slice(0, 6)
        return
      }

      clearTimeout(this.debounceTimer)
      if (/^\d{6}$/.test(val)) {
        this.debounceTimer = setTimeout(() => {
          this.loadData()
        }, 800)
      }
    },
    // 保存设置
    saveSettings() {
      localStorage.setItem('stockQuerySettings', JSON.stringify({
        symbol: this.queryForm.symbol,
        adjustType: this.queryForm.adjustType,
        dateRange: this.queryForm.dateRange
      }))
    },

    // 加载数据 在loadData方法中

    async loadData() {
      if (!this.validateSymbol()) return

      this.loading = true
      try {
        const { data } = await getKline(this.queryForm)
        if (data.length === 0) {
          this.$message.warning('未找到相关股票数据')
          return
        }

        this.rawData = data.sort((a, b) => new Date(a.date) - new Date(b.date))
        this.lastSymbol = this.queryForm.symbol // 保存最后查询的股票代码
        this.signalsData =[]
        this.saveSettings()
        this.updateChart()
        this.updateChartWithSignals()
      } catch (error) {
        this.handleError(error, '数据加载')
      } finally {
        this.loading = false
      }
    },

    // 通用错误处理
    handleError(error, action = '') {
      const defaultMsg = `${action}失败，请检查网络或输入`
      const message = error.response?.data?.message || error.message || defaultMsg
      this.$message.error(message)

      if (error.response?.status === 404) {
        this.queryForm.symbol = ''
      }
    },

    // 输入验证
    validateSymbol() {
      if (!/^\d{6}$/.test(this.queryForm.symbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return false
      }
      return true
    },

    // 增强的回车处理
    handleEnterKey(event) {
      const activeElement = document.activeElement
      if (activeElement?.classList?.contains('el-autocomplete__input')) return

      if (this.queryForm.symbol && !this.loading) {
        this.loadData()
      }
    },
    handleResize() {
      this.chartInstance.resize()
    },

    formatPercentage(value) {
      if (typeof value !== 'number') return '-'
      return `${(value * 100).toFixed(2)}%`
    },

    async handleAnalyze() {

      if (!this.lastSymbol) {
        this.$message.warning('请先查询股票数据')
        return
      }
      this.signalsData = [] // 清空旧信号
      this.analysisData = null // 重置分析数据
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
      const formatDate = (dateStr) => {
        return new Date(dateStr).toISOString().split('T')[0]
      }
      // 生成标记点数据
      const markPoints = this.signalsData.map(signal => {
        // 兼容带时间戳的日期格式（去除时间部分）
        const signalDate = formatDate(signal.date)
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
      }, )// { replaceMerge: ['series'] }) // 明确替换指定系列
    },

// 在methods中添加以下方法
    updateChart() {
      if (!this.chartInstance) return

      // 转换K线数据
      const candleData = this.rawData.map(d => [
        d.open,
        d.close,
        d.low,
        d.high
      ])

      // 转换成交量数据
      const volumeData = this.rawData.map(d => d.volume)

      // 计算移动平均线
      const ma5Data = calculateMA(this.rawData, 5)
      const ma10Data = calculateMA(this.rawData, 10)

      // 准备x轴数据（日期）
      const dates = this.rawData.map(d => d.date)

      // 更新图表选项
      const option = {
        xAxis: [{ data: dates }, { data: dates }],
        series: [
          { data: candleData },          // K线系列
          { data: volumeData },          // 成交量系列
          { data: ma5Data },             // MA5系列
          { data: ma10Data }            // MA10系列
        ]
      }

      this.chartInstance.setOption(option)
      this.handleResize() // 确保图表自适应

      // 如果有信号数据需要显示
      if (this.signalsData.length > 0) {
        this.updateChartWithSignals()
      }
    },
    getWinRateStyle(winRate) {
      if (typeof winRate !== 'number') return {}
      if (winRate > 0.6) return { color: '#67C23A', fontWeight: 'bold' }
      if (winRate < 0.5) return { color: '#F56C6C', fontWeight: 'bold' }
      return {}
    },
    async showAIAnalysis() {
      if (!this.lastSymbol) {
        this.$message.warning('请先查询股票数据')
        return
      }

      this.aiAnalysisDialogVisible = true
      this.aiAnalysisLoading = true
      this.aiAnalysisReport = null

      try {
        // 检查缓存
        const cacheKey = `${this.lastSymbol}_analysis`
        const cachedData = this.getFromCache(cacheKey)

        if (cachedData) {
          this.aiAnalysisReport = cachedData
          this.aiAnalysisLoading = false
          return
        }
        // 新增股票名称查询
        const stockInfo = this.mockSymbols.find(
          item => item.symbol === this.lastSymbol
        );
        const stockName = stockInfo ? stockInfo.name : this.lastSymbol;
        // 使用postChat接口获取分析报告
        const response = await postChat({
          query: `${stockName}（${this.lastSymbol}）的个股分析：
一、盈利能力三维透视
1.收入增长质量
  -近4期《营业总收入》表格显示:
  报告期\t营业总收入\t同比增长率\t基本每股收益\t每股净资产\t销售毛利率\t

  -《营业总收入同比增长率》行业分位值定位
  -非经常损益影响度：（净利润 - 扣非净利润）/净利润
2.利润结构解析
  -毛利率-净利率剪刀差分析：《销售毛利率》vs《销售净利率》
  -收益含金量验证：每股经营现金流 / 基本每股收益
  -可持续增长动能：扣非净利润同比增长率趋势分析
3.主营业务机构分析
  -对比分析[具体产品线]的成本占比与利润贡献的匹配程度
  -找出成本比例高于行业平均但毛利率偏低的业务板块
  -分析主营业务集中度变化（赫芬达尔指数计算）
  -筛选出毛利率高于公司整体水平且收入占比持续提升的业务单元
  -识别收入占比超过30%但毛利率同比下滑超过5%的业务风险点
  -标记客户集中度异常（单一客户收入占比>40%）的警示分析
二、资产负债表健康度诊断
1. 资产效率矩阵
   - 轻资产验证：固定资产周转率
   - 流动性预警：当《流动比率》<2 且《速动比率》<1 时触发警报
   - 存货风险值：存货周转天数历史分位值分析
2. 负债安全边际
   - 资本结构健康度：《资产负债率》行业对比+3年波动标准差
   - 短期偿债压力：现金比率（需货币资金数据）
   - 杠杆质量评估：产权比率同比变化幅度
三、经营质量交叉验证表
验证维度\t核心指标\t健康阈值\t异常信号规则
盈利质量\t扣非净利润/净利润▲\t>85%\t连续两期<70%触发
周转效率\t应收账款周转天数▲\t行业均值±15%\t同比增幅>20%标红
资本回报\t净资产收益率▲\t>15%\t环比下降超5个百分点需注释原因
现金流保障\t每股经营现金流▲\t>基本每股收益▲\t负值立即预警
四、风险预警信号清单
! 重点监控项（最近两期）：
+ 营业总收入同比增速跌破行业P25分位▲
- 存货周转天数连续3期上升且超行业均值▲
! 产权比率同比增幅>30%▲
+ 销售毛利率环比下降超5个百分点▲
五、估值锚点测算模型
每股安全边际 = 每股净资产▲ + 每股未分配利润▲ * 0.7
六、分析结论
1. **核心优势**
   - 高ROE持续性：《净资产收益率》>20%且波动率<15%▲
   - 现金流优势：连续3期每股经营现金流>1元▲

2. **风险聚焦**
   - 债务结构风险：若《短期借款/长期借款》>1.5（需负债明细）
   - 盈利波动风险：《净利润同比增长率》标准差>行业1.5倍▲

3. **估值建议**
   - 折溢价判断：当前PE所处历史百分位▲
   - 安全边际测算：股价/每股净资产▲ 对比行业中枢

注意事项：
单位转换：建议将原始"元"单位转换为"亿元"进行可视化
可比性处理：跨期分析需说明是否采用同口径调整
` ,
          // selected_tools:['stock_zygc_em','stock_balance_sheet_by_report_em','stock_cash_flow_sheet_by_report_em','stock_profit_sheet_by_report_em']
          selected_tools:['stock_zygc_em','stock_financial_abstract_ths','stock_cash_flow_sheet_by_report_em']
        })

        if (response.data && response.data.response) {
          // 使用markdown-it渲染并净化内容
          const rawHtml = md.render(response.data.response)
          this.aiAnalysisReport = DOMPurify.sanitize(rawHtml)


        }
      } catch (error) {
        this.$message.error('AI分析报告生成失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.aiAnalysisLoading = false
      }
    },

    // 缓存相关方法
    saveToCache(key, data) {
      const cacheItem = {
        data,
        timestamp: Date.now()
      }
      this.analysisCache.set(key, cacheItem)
    },

    getFromCache(key) {
      const cacheItem = this.analysisCache.get(key)
      if (!cacheItem) return null

      // 检查是否过期
      if (Date.now() - cacheItem.timestamp > this.cacheExpiration) {
        this.analysisCache.delete(key)
        return null
      }

      return cacheItem.data
    },

    handleAIAnalysisClose() {
      this.aiAnalysisDialogVisible = false
      this.aiAnalysisReport = null
    },

    getMetricStyle(value) {
      if (typeof value !== 'number') return {}
      if (value >= 0.7) return { color: '#67C23A', fontWeight: 'bold' }
      if (value >= 0.5) return { color: '#E6A23C', fontWeight: 'bold' }
      return { color: '#F56C6C', fontWeight: 'bold' }
    },
  }
}
</script>

<style scoped>
.app-container {
  background-color: #fff;
  padding: 20px;
  min-height: 100vh;
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
  height: 700px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-top: 20px;
}

.loading-alert {
  margin: 10px 0;
  padding: 8px 16px;
}

.ai-dialog-content {
  min-height: 400px;
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.ai-analysis-content {
  padding: 20px;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
}

.analysis-section {
  margin-bottom: 24px;
}

.analysis-section h3 {
  color: #409EFF;
  font-size: 18px;
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #409EFF;
  font-weight: 600;
}

.analysis-section h4 {
  color: #303133;
  font-size: 16px;
  margin: 16px 0 12px;
  font-weight: 600;
}

.analysis-section p {
  margin: 12px 0;
  line-height: 1.8;
  color: #606266;
}

.analysis-section strong {
  color: #303133;
  font-weight: 600;
}

.analysis-section ul {
  padding-left: 20px;
  margin: 12px 0;
}

.analysis-section li {
  margin: 8px 0;
  color: #606266;
  line-height: 1.8;
}

.analysis-section ul ul {
  margin: 4px 0;
}

.analysis-section ul ul li {
  margin: 4px 0;
  color: #606266;
}

.analysis-section table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  background-color: #fff;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.analysis-section th {
  background-color: #f5f7fa;
  color: #303133;
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.analysis-section td {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
}

.analysis-section tr:last-child td {
  border-bottom: none;
}

.analysis-section tr:hover td {
  background-color: #f5f7fa;
}

.analysis-section hr {
  margin: 24px 0;
  border: none;
  border-top: 1px solid #ebeef5;
}

.analysis-section blockquote {
  margin: 16px 0;
  padding: 12px 16px;
  background-color: #f5f7fa;
  border-left: 4px solid #409EFF;
  color: #606266;
}

.analysis-section code {
  background-color: #f5f7fa;
  padding: 2px 4px;
  border-radius: 4px;
  color: #409EFF;
  font-family: Consolas, Monaco, 'Andale Mono', monospace;
}

.analysis-section pre {
  background-color: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 12px 0;
}

.analysis-section pre code {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

.analysis-section a {
  color: #409EFF;
  text-decoration: none;
}

.analysis-section a:hover {
  text-decoration: underline;
}

.analysis-section img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 12px 0;
}

.no-analysis {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.ai-analysis-dialog ::v-deep .el-dialog {
  height: 80vh;
  display: flex;
  flex-direction: column;
  margin-top: 10vh !important;
}

.ai-analysis-dialog ::v-deep .el-dialog__body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.ai-analysis-dialog ::v-deep .el-loading-mask {
  background-color: rgba(255, 255, 255, 0.9);
}

.ai-analysis-dialog ::v-deep .el-loading-spinner {
  margin-top: 20vh;
}

.ai-analysis-dialog ::v-deep .el-loading-spinner .circular {
  width: 42px;
  height: 42px;
}

.ai-analysis-dialog ::v-deep .el-loading-spinner .el-loading-text {
  color: #409EFF;
  margin: 3px 0;
  font-size: 14px;
}

/* 增强Markdown内容样式 */
.ai-analysis-content ::v-deep h3 {
  color: #409EFF;
  margin: 1em 0 0.5em;
}

.ai-analysis-content ::v-deep ul {
  padding-left: 2em;
  list-style-type: disc;
}

.ai-analysis-content ::v-deep table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

.ai-analysis-content ::v-deep th,
.ai-analysis-content ::v-deep td {
  padding: 0.8em;
  border: 1px solid #ebeef5;
}

.ai-analysis-content ::v-deep code {
  background-color: #f5f7fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
}

.ai-analysis-content ::v-deep pre {
  background-color: #f5f7fa;
  padding: 1em;
  overflow-x: auto;
}

.ai-analysis-content ::v-deep a {
  color: #409EFF;
  text-decoration: none;
}

.ai-analysis-content ::v-deep a:hover {
  text-decoration: underline;
}
</style>
