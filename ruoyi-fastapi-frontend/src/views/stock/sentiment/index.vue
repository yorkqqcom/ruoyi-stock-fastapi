<template>
  <div class="app-container">
    <!-- 查询条件 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="queryForm" class="demo-form-inline">
        <el-form-item label="股票代码" prop="symbols">
          <el-select
            v-model="queryForm.symbols"
            multiple
            filterable
            remote
            reserve-keyword
            placeholder="请输入股票代码或名称"
            :remote-method="fetchSuggestions"
            :loading="loading"
            style="width: 400px"
          >
            <el-option
              v-for="item in mockSymbols"
              :key="item.symbol"
              :label="item.name"
              :value="item.symbol"
            >
              <span style="float: left">{{ item.symbol }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ item.name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="queryForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="yyyy-MM-dd"
            :picker-options="pickerOptions"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery" :loading="loading" icon="el-icon-search">查询</el-button>
          <el-button @click="resetQuery" icon="el-icon-refresh">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 市场情绪仪表盘 -->
    <el-row :gutter="20" class="dashboard-container">
      <!-- 三维聚类图 -->
      <el-col :span="16">
        <el-card class="box-card" v-loading="loading" element-loading-text="正在分析市场情绪...">
          <div slot="header" class="clearfix">
            <span class="card-title">市场情绪聚类分析</span>
            <el-tooltip content="基于Wasserstein距离的聚类分析，帮助识别市场机制" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <div ref="clusterChart" class="chart"></div>
        </el-card>
      </el-col>

      <!-- 参数面板 -->
      <el-col :span="8">
        <el-card class="box-card" v-loading="loading">
          <div slot="header" class="clearfix">
            <span class="card-title">分析参数</span>
            <el-tooltip content="调整参数以优化分析结果" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <el-form label-position="top">
            <el-form-item label="时间窗口">
              <el-slider
                v-model="params.windowSize"
                :min="10"
                :max="60"
                :step="5"
                show-input
                :marks="{
                  10: '10天',
                  30: '30天',
                  60: '60天'
                }"
              />
            </el-form-item>
            <el-form-item label="聚类数量">
              <el-slider
                v-model="params.nClusters"
                :min="2"
                :max="5"
                :step="1"
                show-input
                :marks="{
                  2: '2类',
                  3: '3类',
                  4: '4类',
                  5: '5类'
                }"
              />
            </el-form-item>
            <el-form-item label="距离度量">
              <el-select v-model="params.distanceMetric" placeholder="请选择" style="width: 100%">
                <el-option label="Wasserstein距离" value="wasserstein">
                  <span>Wasserstein距离</span>
                  <el-tooltip content="更适合捕捉分布特征的度量方法" placement="right">
                    <i class="el-icon-info"></i>
                  </el-tooltip>
                </el-option>
                <el-option label="最大均值差异" value="mmd">
                  <span>最大均值差异</span>
                  <el-tooltip content="基于核方法的分布度量" placement="right">
                    <i class="el-icon-info"></i>
                  </el-tooltip>
                </el-option>
                <el-option label="欧氏距离" value="euclidean">
                  <span>欧氏距离</span>
                  <el-tooltip content="传统的点对点距离度量" placement="right">
                    <i class="el-icon-info"></i>
                  </el-tooltip>
                </el-option>
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 股票机制分析面板 -->
    <el-row :gutter="20" class="regime-container">
      <el-col :span="24">
        <el-card class="box-card" v-loading="loading">
          <div slot="header" class="clearfix">
            <span class="card-title">股票机制分析</span>
            <el-tooltip content="分析每只股票的市场机制" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <el-tabs v-model="activeStock" type="card">
            <el-tab-pane
              v-for="symbol in queryForm.symbols"
              :key="symbol"
              :label="getStockName(symbol)"
              :name="symbol"
            >
              <transition-group name="regime-fade" tag="div" class="regime-list">
                <div
                  v-for="regime in getStockRegimes(symbol)"
                  :key="regime.id"
                  :class="['regime-card', regime.type]"
                >
                  <div class="regime-header">
                    <h4>{{ regime.name }}</h4>
                    <el-tag :type="getRegimeType(regime.type)">{{ regime.type }}</el-tag>
                  </div>
                  <div class="regime-stats">
                    <div class="stat-item">
                      <span class="label">波动率:</span>
                      <span class="value">{{ (regime.volatility * 100).toFixed(2) }}%</span>
                    </div>
                    <div class="stat-item">
                      <span class="label">收益率:</span>
                      <span class="value" :class="getReturnClass(regime.mean_return)">
                        {{ (regime.mean_return * 100).toFixed(2) }}%
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="label">时间范围:</span>
                      <span class="value">{{ regime.start_date }} 至 {{ regime.end_date }}</span>
                    </div>
                  </div>
                  <div class="regime-chart" :ref="'regimeChart' + regime.id"></div>
                </div>
              </transition-group>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <!-- 信号面板 -->
    <el-row :gutter="20" class="signal-container">
      <el-col :span="24">
        <el-card class="box-card" v-loading="loading">
          <div slot="header" class="clearfix">
            <span class="card-title">交易信号</span>
            <el-tooltip content="基于市场机制生成的交易建议" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <el-table
            :data="signals"
            style="width: 100%"
            :row-class-name="getSignalRowClass"
            border
            stripe
          >
            <el-table-column prop="date" label="日期" width="120" sortable />
            <el-table-column prop="type" label="信号类型" width="150">
              <template slot-scope="scope">
                <el-tag :type="getSignalType(scope.row.type)" effect="dark">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="200">
              <template slot-scope="scope">
                <el-progress
                  :percentage="scope.row.confidence * 100"
                  :color="getConfidenceColor(scope.row.confidence)"
                  :format="format"
                />
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 指标提示和交易建议面板 -->
    <el-row :gutter="20" class="advice-container">
      <el-col :span="12">
        <el-card class="box-card" v-loading="loading">
          <div slot="header" class="clearfix">
            <span class="card-title">指标提示</span>
            <el-tooltip content="关键市场指标分析" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <div class="indicator-list">
            <div v-for="(indicator, index) in indicators" :key="index" class="indicator-item">
              <el-alert
                :title="indicator.name"
                :type="indicator.type"
                :description="indicator.description"
                show-icon
                :closable="false"
                effect="dark"
              />
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="box-card" v-loading="loading">
          <div slot="header" class="clearfix">
            <span class="card-title">交易建议</span>
            <el-tooltip content="基于多维度分析的交易建议" placement="top">
              <i class="el-icon-info"></i>
            </el-tooltip>
          </div>
          <div class="trading-advice">
            <el-timeline>
              <el-timeline-item
                v-for="(advice, index) in tradingAdvice"
                :key="index"
                :type="advice.type"
                :color="advice.color"
                :timestamp="advice.time"
                size="large"
              >
                <h4>{{ advice.title }}</h4>
                <p>{{ advice.content }}</p>
                <div class="advice-details" v-if="advice.details">
                  <p v-for="(detail, idx) in advice.details" :key="idx">
                    {{ detail }}
                  </p>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import 'echarts-gl'  // 引入 ECharts 3D 扩展
import { getStockSentiment } from '@/api/stock/sentiment'
import { getstocklist } from '@/api/stock/kline'

export default {
  name: 'MarketSentiment',
  data() {
    return {
      loading: false,
      queryForm: {
        symbols: ['600519'],
        dateRange: [
          new Date(Date.now() - 3 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          new Date().toISOString().split('T')[0]
        ]
      },
      params: {
        windowSize: 30,
        nClusters: 3,
        distanceMetric: 'wasserstein'
      },
      currentRegimes: [],
      signals: [],
      clusterChart: null,
      regimeCharts: {},
      mockSymbols: [], // 股票列表
      debounceTimer: null, // 防抖定时器
      lastSymbol: '', // 最后查询的股票代码
      indicators: [],
      tradingAdvice: [],
      pickerOptions: {
        shortcuts: [{
          text: '最近一周',
          onClick(picker) {
            const end = new Date()
            const start = new Date()
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
            picker.$emit('pick', [start, end])
          }
        }, {
          text: '最近一个月',
          onClick(picker) {
            const end = new Date()
            const start = new Date()
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
            picker.$emit('pick', [start, end])
          }
        }, {
          text: '最近三个月',
          onClick(picker) {
            const end = new Date()
            const start = new Date()
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
            picker.$emit('pick', [start, end])
          }
        }, {
          text: '最近一年',
          onClick(picker) {
            const end = new Date()
            const start = new Date()
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 365)
            picker.$emit('pick', [start, end])
          }
        }, {
          text: '最近三年',
          onClick(picker) {
            const end = new Date()
            const start = new Date()
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 365 * 3)
            picker.$emit('pick', [start, end])
          }
        }]
      },
      activeStock: '600519',
      analysisData: null
    }
  },
  created() {
    this.loadStockList()
  },
  mounted() {
    this.initCharts()
  },
  beforeDestroy() {
    this.disposeCharts()
  },
  methods: {
    // 加载股票列表
    async loadStockList() {
      try {
        const response = await getstocklist()
        this.mockSymbols = response.data || []
      } catch (error) {
        console.error('股票列表加载失败:', error)
        this.$message.error('股票列表加载失败')
      }
    },

    // 股票代码选择处理
    handleSelectSymbol(item) {
      this.queryForm.symbol = item.symbol
      this.loadData()
    },

    // 自动补全逻辑
    async fetchSuggestions(queryString, cb) {
      if (typeof cb !== 'function') {
        console.warn('Callback is not a function')
        return
      }
      
      try {
        const source = Array.isArray(this.mockSymbols) ? this.mockSymbols : []
        const results = source.filter(item =>
          item.symbol.includes(queryString) ||
          item.name.includes(queryString)
        ).map(item => ({
          value: item.symbol,
          label: item.name,
          symbol: item.symbol,
          name: item.name
        }))
        
        cb(results)
      } catch (error) {
        console.error('获取股票建议失败:', error)
        cb([])
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

    // 输入验证
    validateSymbol() {
      if (!/^\d{6}$/.test(this.queryForm.symbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return false
      }
      return true
    },

    // 加载数据
    async loadData() {
      if (!this.validateSymbols()) return

      this.loading = true
      try {
        // 确保日期格式正确
        const startDate = this.queryForm.dateRange[0] ? new Date(this.queryForm.dateRange[0]).toISOString().split('T')[0] : ''
        const endDate = this.queryForm.dateRange[1] ? new Date(this.queryForm.dateRange[1]).toISOString().split('T')[0] : ''

        // 构建请求参数
        const requestParams = {
          symbol: this.queryForm.symbols[0], // 暂时只处理第一只股票
          start_date: startDate,
          end_date: endDate,
          params: {
            windowSize: Number(this.params.windowSize),
            nClusters: Number(this.params.nClusters),
            distanceMetric: this.params.distanceMetric
          }
        }

        console.log('发送请求数据:', JSON.stringify(requestParams, null, 2)) // 添加详细日志
        const response = await getStockSentiment(requestParams)
        
        if (!response || !response.data) {
          throw new Error('返回数据为空')
        }

        // 确保数据格式正确
        const processedData = {
          volatility: parseFloat(response.data.volatility || 0),
          mean_return: parseFloat(response.data.mean_return || 0),
          correlation: parseFloat(response.data.correlation || 0),
          regime: response.data.regime || 'neutral',
          sentiment: parseFloat(response.data.sentiment || 0),
          trend: response.data.trend || 'neutral'
        }

        this.analysisData = processedData
        this.$nextTick(() => {
          this.initCharts()
          this.updateCharts(processedData)
          this.updateIndicators(processedData)
          this.updateTradingAdvice(processedData)
        })
      } catch (error) {
        console.error('获取数据失败:', error)
        let errorMessage = '获取数据失败'
        if (error.response) {
          // 处理422错误
          if (error.response.status === 422) {
            const details = error.response.data.detail
            if (Array.isArray(details)) {
              errorMessage = details.map(err => err.msg).join('\n')
            } else if (typeof details === 'string') {
              errorMessage = details
            }
            // 添加更详细的错误信息
            console.error('请求参数:', requestParams)
            console.error('错误详情:', details)
          } else {
            errorMessage = error.response.data?.message || error.message
          }
        }
        this.$message.error(errorMessage)
      } finally {
        this.loading = false
      }
    },
    initCharts() {
      // 初始化聚类图
      this.clusterChart = echarts.init(this.$refs.clusterChart)
      
      // 设置图表配置
      const option = {
        title: {
          text: '市场情绪聚类分析',
          left: 'center'
        },
        tooltip: {},
        xAxis3D: {
          type: 'value'
        },
        yAxis3D: {
          type: 'value'
        },
        zAxis3D: {
          type: 'value'
        },
        grid3D: {},
        series: [{
          type: 'scatter3D',
          data: []
        }]
      }
      
      this.clusterChart.setOption(option)
    },
    disposeCharts() {
      if (this.clusterChart) {
        this.clusterChart.dispose()
      }
      Object.values(this.regimeCharts).forEach(chart => {
        if (chart) {
          chart.dispose()
        }
      })
    },
    updateCharts(data) {
      if (!data) {
        console.warn('No data received')
        return
      }
      
      // 确保数据格式正确
      const clusterData = [{
        volatility: data.volatility || 0,
        return: data.mean_return || 0,
        correlation: data.correlation || 0,
        date: new Date().toISOString().split('T')[0],
        regime: data.regime || 'unknown'
      }]

      // 更新聚类图
      const clusterOption = {
        title: {
          text: '市场情绪聚类分析',
          left: 'center'
        },
        tooltip: {
          formatter: function(params) {
            return `日期: ${params.data.date}<br/>
                    机制: ${params.data.regime}<br/>
                    波动率: ${(params.data.volatility * 100).toFixed(2)}%<br/>
                    收益率: ${(params.data.return * 100).toFixed(2)}%`
          }
        },
        xAxis3D: {
          type: 'value',
          name: '波动率'
        },
        yAxis3D: {
          type: 'value',
          name: '收益率'
        },
        zAxis3D: {
          type: 'value',
          name: '相关性'
        },
        grid3D: {
          boxWidth: 200,
          boxHeight: 200,
          boxDepth: 200
        },
        series: [{
          type: 'scatter3D',
          data: clusterData.map((cluster, index) => ({
            value: [cluster.volatility, cluster.return, cluster.correlation],
            itemStyle: {
              color: this.getClusterColor(index)
            },
            date: cluster.date,
            regime: cluster.regime,
            volatility: cluster.volatility,
            return: cluster.return
          }))
        }]
      }
      this.clusterChart.setOption(clusterOption)
    },
    updateRegimes(regimes) {
      if (!regimes || !Array.isArray(regimes)) {
        console.warn('Invalid regimes data:', regimes)
        return
      }
      
      this.currentRegimes = regimes.map(regime => {
        const processedRegime = { ...regime }
        if (regime.date) {
          try {
            processedRegime.date = new Date(regime.date).toISOString().split('T')[0]
          } catch (e) {
            console.warn('Invalid date in regime:', regime.date)
            processedRegime.date = ''
          }
        }
        return {
          ...processedRegime,
          id: `regime-${regime.id}`
        }
      })
      
      this.$nextTick(() => {
        this.currentRegimes.forEach(regime => {
          this.initRegimeChart(regime)
        })
      })
    },
    initRegimeChart(regime) {
      const chartDom = this.$refs[`regimeChart${regime.id}`][0]
      const chart = echarts.init(chartDom)
      
      const option = {
        title: {
          text: '相关性热力图',
          left: 'center'
        },
        tooltip: {
          position: 'top'
        },
        grid: {
          height: '50%',
          top: '10%'
        },
        xAxis: {
          type: 'category',
          data: regime.correlation.labels,
          splitArea: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: regime.correlation.labels,
          splitArea: {
            show: true
          }
        },
        visualMap: {
          min: -1,
          max: 1,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '15%'
        },
        series: [{
          name: '相关性',
          type: 'heatmap',
          data: regime.correlation.data,
          label: {
            show: true
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }
      
      chart.setOption(option)
      this.regimeCharts[regime.id] = chart
    },
    updateSignals(signals) {
      if (!signals || !Array.isArray(signals)) {
        console.warn('Invalid signals data:', signals)
        return
      }
      
      this.signals = signals.map(signal => {
        const processedSignal = { ...signal }
        if (signal.date) {
          try {
            processedSignal.date = new Date(signal.date).toISOString().split('T')[0]
          } catch (e) {
            console.warn('Invalid date in signal:', signal.date)
            processedSignal.date = ''
          }
        }
        return processedSignal
      })
    },
    getClusterColor(index) {
      const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
      return colors[index % colors.length]
    },
    getSignalType(type) {
      const types = {
        'BUY_SPREAD': 'success',
        'SELL_SPREAD': 'danger',
        'REGIME_CHANGE': 'warning',
        'HIGH_VOLATILITY': 'danger',
        'LOW_VOLATILITY': 'info'
      }
      return types[type] || 'info'
    },
    getConfidenceColor(confidence) {
      if (confidence >= 0.8) return '#67C23A'
      if (confidence >= 0.6) return '#E6A23C'
      return '#F56C6C'
    },
    handleQuery() {
      this.loadData()
    },
    // 更新指标提示
    updateIndicators(data) {
      if (!data) return
      
      this.indicators = []
      
      // 波动率指标
      if (data.volatility !== undefined) {
        const volatility = parseFloat(data.volatility)
        this.indicators.push({
          name: '波动率指标',
          type: volatility > 0.02 ? 'warning' : 'success',
          description: `当前波动率为 ${(volatility * 100).toFixed(2)}%，${volatility > 0.02 ? '市场波动较大，建议谨慎操作' : '市场相对稳定'}`
        })
      }

      // 趋势指标
      if (data.trend) {
        this.indicators.push({
          name: '趋势指标',
          type: data.trend === 'up' ? 'success' : data.trend === 'down' ? 'danger' : 'info',
          description: `当前趋势为${data.trend === 'up' ? '上升' : data.trend === 'down' ? '下降' : '震荡'}，${this.getTrendAdvice(data.trend)}`
        })
      }

      // 市场情绪指标
      if (data.sentiment !== undefined) {
        const sentiment = parseFloat(data.sentiment)
        this.indicators.push({
          name: '市场情绪',
          type: sentiment > 0.6 ? 'success' : sentiment < 0.4 ? 'danger' : 'warning',
          description: `市场情绪指数为 ${(sentiment * 100).toFixed(0)}，${this.getSentimentDescription(sentiment)}`
        })
      }

      // 市场机制分析
      if (data.regime) {
        const regimeDescriptions = {
          'high_volatility': '高波动状态',
          'uptrend': '上升趋势',
          'downtrend': '下降趋势',
          'sideways': '震荡状态',
          'bull': '牛市',
          'bear': '熊市',
          'neutral': '中性'
        }
        
        const regimeType = data.regime
        const regimeDesc = regimeDescriptions[regimeType] || '未知状态'
        
        this.indicators.push({
          name: '市场机制分析',
          type: this.getRegimeType(regimeType),
          description: `当前市场处于${regimeDesc}。${this.getRegimeFeatures(data)}`
        })
      }
    },

    // 获取市场机制特征
    getRegimeFeatures(data) {
      if (!data) return '建议观望'
      
      const features = []
      
      // 添加波动率特征
      if (data.volatility !== undefined) {
        const volatility = parseFloat(data.volatility)
        if (volatility > 0.02) {
          features.push('波动率较高')
        } else if (volatility < 0.01) {
          features.push('波动率较低')
        }
      }
      
      // 添加收益率特征
      if (data.mean_return !== undefined) {
        const returnValue = parseFloat(data.mean_return)
        if (returnValue > 0.01) {
          features.push('收益率较好')
        } else if (returnValue < -0.01) {
          features.push('收益率较差')
        }
      }
      
      // 添加相关性特征
      if (data.correlation !== undefined) {
        const correlation = parseFloat(data.correlation)
        if (correlation > 0.7) {
          features.push('相关性较强')
        } else if (correlation < 0.3) {
          features.push('相关性较弱')
        }
      }
      
      // 根据特征生成建议
      let advice = '建议'
      if (features.length > 0) {
        advice += `：${features.join('，')}，`
      }
      
      // 添加具体操作建议
      const regimeType = data.regime || 'neutral'
      const regimeAdvice = {
        'high_volatility': '控制仓位，设置严格止损，避免追高',
        'uptrend': '可以适当增加仓位，关注基本面变化，把握波段机会',
        'downtrend': '观望为主，等待企稳信号，考虑分批建仓',
        'sideways': '高抛低吸，控制仓位，等待突破信号',
        'bull': '可以积极布局，但注意风险控制',
        'bear': '建议减仓观望，等待市场企稳',
        'neutral': '保持观望，等待明确信号'
      }
      
      advice += regimeAdvice[regimeType] || '保持观望'
      return advice
    },

    // 更新交易建议
    updateTradingAdvice(data) {
      if (!data) return
      
      this.tradingAdvice = []
      const now = new Date().toLocaleString()

      // 基于波动率的建议
      if (data.volatility) {
        const volatility = parseFloat(data.volatility)
        this.tradingAdvice.push({
          title: '波动率分析',
          content: this.getVolatilityAdvice(volatility),
          type: volatility > 0.02 ? 'warning' : 'success',
          color: volatility > 0.02 ? '#E6A23C' : '#67C23A',
          time: now
        })
      }

      // 基于趋势的建议
      if (data.trend) {
        this.tradingAdvice.push({
          title: '趋势分析',
          content: this.getTrendAdvice(data.trend),
          type: data.trend === 'up' ? 'success' : data.trend === 'down' ? 'danger' : 'info',
          color: data.trend === 'up' ? '#67C23A' : data.trend === 'down' ? '#F56C6C' : '#909399',
          time: now
        })
      }

      // 基于市场情绪的建议
      if (data.sentiment) {
        this.tradingAdvice.push({
          title: '市场情绪分析',
          content: this.getSentimentAdvice(data.sentiment),
          type: data.sentiment > 0.6 ? 'success' : data.sentiment < 0.4 ? 'danger' : 'warning',
          color: data.sentiment > 0.6 ? '#67C23A' : data.sentiment < 0.4 ? '#F56C6C' : '#E6A23C',
          time: now
        })
      }

      // 基于聚类分析的建议
      if (data.clusters && data.clusters.length > 0) {
        const currentCluster = data.clusters[data.clusters.length - 1]
        this.tradingAdvice.push({
          title: '市场机制分析',
          content: this.getClusterAdvice(currentCluster),
          type: this.getClusterType(currentCluster.regime),
          color: this.getClusterColor(currentCluster.regime),
          time: now
        })
      }
    },

    // 获取趋势建议
    getTrendAdvice(trend) {
      const advice = {
        up: '可以考虑逢低买入，但要注意设置止损位',
        down: '建议观望或减仓，等待企稳信号',
        flat: '市场处于震荡期，建议高抛低吸'
      }
      return advice[trend] || '建议观望'
    },

    // 获取波动率建议
    getVolatilityAdvice(volatility) {
      if (volatility > 0.02) {
        return '市场波动较大，建议：\n1. 控制仓位\n2. 设置严格止损\n3. 避免追高'
      } else {
        return '市场相对稳定，建议：\n1. 可以适当增加仓位\n2. 关注基本面变化\n3. 把握波段机会'
      }
    },

    // 获取市场情绪描述
    getSentimentDescription(sentiment) {
      if (sentiment > 0.6) {
        return '市场情绪乐观，但需警惕过热风险'
      } else if (sentiment < 0.4) {
        return '市场情绪低迷，可能存在超跌机会'
      } else {
        return '市场情绪中性，建议观望为主'
      }
    },

    // 获取市场情绪建议
    getSentimentAdvice(sentiment) {
      if (sentiment > 0.6) {
        return '市场情绪过热，建议：\n1. 注意风险控制\n2. 避免追高\n3. 考虑逐步减仓'
      } else if (sentiment < 0.4) {
        return '市场情绪低迷，建议：\n1. 关注超跌机会\n2. 分批建仓\n3. 设置合理止损'
      } else {
        return '市场情绪平稳，建议：\n1. 保持观望\n2. 关注基本面变化\n3. 等待明确信号'
      }
    },

    // 获取聚类建议
    getClusterAdvice(cluster) {
      const advice = {
        'high_volatility': '市场处于高波动状态，建议：\n1. 控制仓位\n2. 设置严格止损\n3. 避免追高',
        'uptrend': '市场处于上升趋势，建议：\n1. 可以适当增加仓位\n2. 关注基本面变化\n3. 把握波段机会',
        'downtrend': '市场处于下降趋势，建议：\n1. 观望为主\n2. 等待企稳信号\n3. 考虑分批建仓',
        'sideways': '市场处于震荡期，建议：\n1. 高抛低吸\n2. 控制仓位\n3. 等待突破信号'
      }
      return advice[cluster.regime] || '建议观望'
    },

    // 获取聚类类型对应的样式
    getClusterType(regime) {
      const types = {
        'high_volatility': 'warning',
        'uptrend': 'success',
        'downtrend': 'danger',
        'sideways': 'info'
      }
      return types[regime] || 'info'
    },

    // 获取聚类颜色
    getClusterColor(regime) {
      const colors = {
        'high_volatility': '#E6A23C',
        'uptrend': '#67C23A',
        'downtrend': '#F56C6C',
        'sideways': '#909399'
      }
      return colors[regime] || '#909399'
    },
    resetQuery() {
      this.queryForm = {
        symbols: ['600519'],
        dateRange: [
          new Date(Date.now() - 3 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          new Date().toISOString().split('T')[0]
        ]
      }
      this.handleQuery()
    },
    format(percentage) {
      return percentage.toFixed(1) + '%'
    },
    getRegimeType(type) {
      const types = {
        'high_volatility': 'warning',
        'uptrend': 'success',
        'downtrend': 'danger',
        'sideways': 'info'
      }
      return types[type] || 'info'
    },
    getReturnClass(return_value) {
      return return_value > 0 ? 'positive-return' : 'negative-return'
    },
    getSignalRowClass({ row }) {
      return `signal-row-${row.type.toLowerCase()}`
    },
    getStockName(symbol) {
      const stock = this.mockSymbols.find(s => s.symbol === symbol)
      return stock ? `${symbol} ${stock.name}` : symbol
    },
    getStockRegimes(symbol) {
      if (!this.analysisData || !this.analysisData.regimes) return []
      return this.analysisData.regimes[symbol] || []
    },
    validateSymbols() {
      if (!this.queryForm.symbols || this.queryForm.symbols.length === 0) {
        this.$message.warning('请至少选择一只股票')
        return false
      }
      
      // 验证每个股票代码
      for (const symbol of this.queryForm.symbols) {
        if (!/^\d{6}$/.test(symbol)) {
          this.$message.warning(`股票代码 ${symbol} 格式不正确，请输入6位数字`)
          return false
        }
      }
      
      return true
    }
  }
}
</script>

<style scoped>
.app-container {
  padding: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.dashboard-container {
  margin-top: 20px;
}

.chart {
  height: 500px;
}

.regime-container {
  margin-top: 20px;
}

.regime-list {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.regime-card {
  flex: 1;
  min-width: 300px;
  padding: 20px;
  border-radius: 8px;
  background: #f5f7fa;
  transition: all 0.3s;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.regime-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 16px 0 rgba(0,0,0,0.2);
}

.regime-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.regime-header h4 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.regime-stats {
  margin-bottom: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #606266;
}

.stat-item .label {
  font-weight: 500;
}

.stat-item .value {
  font-weight: 600;
}

.positive-return {
  color: #67C23A;
}

.negative-return {
  color: #F56C6C;
}

.regime-chart {
  height: 200px;
  margin-top: 15px;
}

.regime-fade-enter-active,
.regime-fade-leave-active {
  transition: all 0.5s;
}

.regime-fade-enter,
.regime-fade-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

.signal-container {
  margin-top: 20px;
}

.symbol-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
}

.symbol-code {
  color: #409EFF;
  font-weight: 600;
  margin-right: 15px;
}

.symbol-name {
  color: #666;
  font-size: 0.9em;
  overflow: hidden;
  text-overflow: ellipsis;
}

::v-deep .light-input .el-input__inner {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
  color: #303133 !important;
}

.advice-container {
  margin-top: 20px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.indicator-item {
  margin-bottom: 10px;
}

.trading-advice {
  padding: 10px;
}

.advice-details {
  margin-top: 10px;
  padding-left: 20px;
  color: #606266;
}

.advice-details p {
  margin: 5px 0;
  line-height: 1.5;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.el-icon-info {
  margin-left: 8px;
  color: #909399;
  cursor: pointer;
}

.signal-row-buy_spread {
  background-color: rgba(103, 194, 58, 0.1);
}

.signal-row-sell_spread {
  background-color: rgba(245, 108, 108, 0.1);
}

.signal-row-high_volatility {
  background-color: rgba(230, 162, 60, 0.1);
}

.signal-row-regime_change {
  background-color: rgba(144, 147, 153, 0.1);
}

::v-deep .el-card__header {
  padding: 15px 20px;
  border-bottom: 1px solid #EBEEF5;
  box-sizing: border-box;
}

::v-deep .el-card__body {
  padding: 20px;
}

::v-deep .el-timeline-item__node--large {
  width: 16px;
  height: 16px;
}

::v-deep .el-timeline-item__content {
  color: #606266;
}

::v-deep .el-timeline-item__timestamp {
  color: #909399;
  font-size: 13px;
}
</style> 