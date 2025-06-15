<template>
  <div class="app-container">
    <!-- 查询条件 -->
    <el-form :inline="true" style="margin-bottom: 5px">
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
      <el-button type="primary" @click="refreshAllData" icon="el-icon-search" :loading="loading">查询</el-button>
    </el-form>
    <el-row :gutter="20">
      <!-- 市场情绪分析卡片 -->
      <el-col :span="6">
        <el-card class="box-card">
          <div slot="header" class="clearfix">
            <span>市场情绪分析</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshSentimentAnalysis">刷新</el-button>
          </div>
          <div class="sentiment-analysis">
            <el-row :gutter="16">
              <el-col :span="8">
                <div class="sentiment-score">
                  <div class="score-title">情绪得分</div>
                  <div class="score-value" :class="getSentimentClass(sentimentData.sentiment_score)">
                    {{ sentimentData.sentiment_score }}%
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="market-trend">
                  <div class="trend-title">市场趋势</div>
                  <div class="trend-value" :class="getTrendClass(sentimentData.market_trend)">
                    {{ getTrendText(sentimentData.market_trend) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="confidence">
                  <div class="confidence-title">预测置信度</div>
                  <div class="confidence-value">
                    {{ sentimentData.confidence }}%
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>

      <!-- 技术指标分析 -->
      <el-col :span="18">
        <el-card class="box-card">
          <div slot="header" class="clearfix">
            <span>技术指标分析</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshTechnicalIndicators">刷新</el-button>
          </div>
          <div class="technical-indicators">
            <el-row :gutter="20">
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">RSI</div>
                  <div class="indicator-value" :class="getIndicatorClass(technicalData && technicalData.indicators && technicalData.indicators.RSI && technicalData.indicators.RSI.signal || 'neutral')">
                    {{ (technicalData && technicalData.indicators && technicalData.indicators.RSI && technicalData.indicators.RSI.value || 0).toFixed(2) }}
                  </div>
                  <div class="indicator-signal">{{ getSignalText(technicalData && technicalData.indicators && technicalData.indicators.RSI && technicalData.indicators.RSI.signal || 'neutral') }}</div>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">MACD</div>
                  <div class="indicator-value" :class="getIndicatorClass(technicalData && technicalData.indicators && technicalData.indicators.MACD && technicalData.indicators.MACD.signal || 'neutral')">
                    {{ getMACDValue(technicalData && technicalData.indicators && technicalData.indicators.MACD) }}
                  </div>
                  <div class="indicator-signal">{{ getSignalText(technicalData && technicalData.indicators && technicalData.indicators.MACD && technicalData.indicators.MACD.signal || 'neutral') }}</div>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">ATR</div>
                  <div class="indicator-value">
                    {{ technicalData && technicalData.indicators && technicalData.indicators.ATR && technicalData.indicators.ATR.value ? technicalData.indicators.ATR.value.toFixed(2) : '-' }}
                  </div>
                  <div class="indicator-signal">波动率指标</div>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">布林带</div>
                  <div class="indicator-value" :class="getIndicatorClass(technicalData && technicalData.indicators && technicalData.indicators.Bollinger_Bands && technicalData.indicators.Bollinger_Bands.signal || 'neutral')">
                    {{ getBBValue(technicalData && technicalData.indicators && technicalData.indicators.Bollinger_Bands) }}
                  </div>
                  <div class="indicator-signal">{{ getSignalText(technicalData && technicalData.indicators && technicalData.indicators.Bollinger_Bands && technicalData.indicators.Bollinger_Bands.signal || 'neutral') }}</div>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">成交量比率</div>
                  <div class="indicator-value" :class="getVolumeRatioClass(technicalData && technicalData.indicators && technicalData.indicators.Volume_Ratio)">
                    {{ technicalData && technicalData.indicators && technicalData.indicators.Volume_Ratio && technicalData.indicators.Volume_Ratio.value ? technicalData.indicators.Volume_Ratio.value.toFixed(2) : '-' }}
                  </div>
                  <div class="indicator-signal">相对成交量</div>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="indicator-item">
                  <div class="indicator-title">价格动量</div>
                  <div class="indicator-value" :class="getMomentumClass(technicalData && technicalData.indicators && technicalData.indicators.Momentum)">
                    {{ technicalData && technicalData.indicators && technicalData.indicators.Momentum && technicalData.indicators.Momentum.value ? (technicalData.indicators.Momentum.value * 100).toFixed(2) + '%' : '-' }}
                  </div>
                  <div class="indicator-signal">10日动量</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" >
      <!-- 市场预测图表 -->
      <el-col :span="24">
        <el-card class="box-card">
          <div slot="header" class="clearfix">
            <span>市场预测</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshMarketPrediction">刷新</el-button>
          </div>
          <div class="prediction-charts">
            <!-- 预测准确率对比 -->
            <div class="prediction-accuracy">
              <div class="accuracy-title">预测准确率分析</div>
              <el-row :gutter="20">
                <el-col :span="6" v-for="(accuracy, type) in formattedPredictionAccuracies" :key="type">
                  <div class="accuracy-item">
                    <div class="accuracy-label">{{ getChartTitle(type) }}</div>
                    <div class="accuracy-metrics">
                      <div class="metric-item">
                        <span class="metric-label">综合准确率</span>
                        <span class="metric-value" :class="getAccuracyClass(accuracy.total)">
                          {{ accuracy.total }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">方向准确率</span>
                        <span class="metric-value" :class="getAccuracyClass(accuracy.direction)">
                          {{ accuracy.direction }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">RMSE</span>
                        <span class="metric-value" :class="getRMSEClass(accuracy.rmse)">
                          {{ accuracy.rmse }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">MAE</span>
                        <span class="metric-value" :class="getRMSEClass(accuracy.mae)">
                          {{ accuracy.mae }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">R²</span>
                        <span class="metric-value" :class="getR2Class(accuracy.r2)">
                          {{ accuracy.r2 }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">相对误差</span>
                        <span class="metric-value" :class="getErrorClass(accuracy.relative_error)">
                          {{ accuracy.relative_error }}
                        </span>
                      </div>
                      <div class="metric-item">
                        <span class="metric-label">预测偏差</span>
                        <span class="metric-value" :class="getBiasClass(accuracy.bias)">
                          {{ accuracy.bias }}
                        </span>
                      </div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
            <!-- 预测图表 -->
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col :span="12">
                <div class="chart-item">
                  <div class="chart-title">日线预测</div>
                  <div ref="dailyChart" class="chart-container"></div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="chart-item">
                  <div class="chart-title">5分钟预测</div>
                  <div ref="minute5Chart" class="chart-container"></div>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col :span="12">
                <div class="chart-item">
                  <div class="chart-title">15分钟预测</div>
                  <div ref="minute15Chart" class="chart-container"></div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="chart-item">
                  <div class="chart-title">1小时预测</div>
                  <div ref="minute60Chart" class="chart-container"></div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24" >
      <!-- 均值回归分析 -->
      <el-col :span="12">
        <el-card class="box-card">
          <div slot="header" class="clearfix">
            <span>均值回归分析</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshMeanReversion">刷新</el-button>
          </div>
          <div class="mean-reversion">
            <div class="trading-opportunities">
              <div class="opportunities-title">交易机会</div>
              <el-table :data="sortedTradingOpportunities" style="width: 100%" height="400">
                <el-table-column prop="date" label="日期" width="120">
                  <template slot-scope="scope">
                    {{ formatDate(scope.row.date) }}
                  </template>
                </el-table-column>
                <el-table-column prop="signal" label="信号" width="100">
                  <template slot-scope="scope">
                    <el-tag :type="scope.row.signal === 'buy' ? 'success' : 'danger'">
                      {{ scope.row.signal === 'buy' ? '买入' : '卖出' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="buy_price" label="买入价格" width="120">
                  <template slot-scope="scope">
                    {{ scope.row.buy_price ? scope.row.buy_price.toFixed(2) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="sell_price" label="卖出价格" width="120">
                  <template slot-scope="scope">
                    {{ scope.row.sell_price ? scope.row.sell_price.toFixed(2) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="profit" label="预期收益" width="120">
                  <template slot-scope="scope">
                    <span :class="getProfitClass(scope.row.expected_return)">
                      {{ scope.row.expected_return ? scope.row.expected_return.toFixed(2) : '-' }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="profit_percentage" label="收益率" width="120">
                  <template slot-scope="scope">
                    <span :class="getProfitClass(scope.row.return_rate)">
                      {{ scope.row.return_rate ? scope.row.return_rate.toFixed(2) + '%' : '-' }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 新闻分析 -->
      <el-col :span="12">
        <el-card class="box-card">
          <div slot="header" class="clearfix">
            <span>新闻分析</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshNewsAnalysis">刷新</el-button>
          </div>
          <div class="news-analysis">
            <div class="sentiment-distribution">
              <div class="distribution-title">情感分布</div>
              <div ref="newsChart" style="width: 100%; height: 200px"></div>
            </div>
            <div class="news-list">
              <el-table :data="newsData.news_list" style="width: 100%" height="200">
                <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip>
                  <template slot-scope="scope">
                    <div class="news-title">{{ scope.row.title }}</div>
                  </template>
                </el-table-column>
                <el-table-column prop="sentiment" label="情感" width="100">
                  <template slot-scope="scope">
                    <el-tag :type="getNewsSentimentType(scope.row.sentiment)">
                      {{ getNewsSentimentText(scope.row.sentiment) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="publish_time" label="发布时间" width="180">
                  <template slot-scope="scope">
                    {{ formatDateTime(scope.row.publish_time) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getSentimentAnalysis, getMarketPrediction, getNewsAnalysis, getTechnicalIndicators, getMeanReversionAnalysis } from '@/api/stock/ai-market'
import { getstocklist } from '@/api/stock/kline'

export default {
  name: 'AIMarketAnalysis',
  data() {
    return {
      sentimentData: {
        sentiment_score: 0,
        market_trend: 'neutral',
        confidence: 0
      },
      predictionData: {
        predictions: [],
        actual_prices: [],
        accuracy: 0,
        daily: {},
        minute_5: {},
        minute_15: {},
        minute_60: {}
      },
      newsData: {
        news_list: [],
        sentiment_distribution: {
          positive: 0,
          neutral: 0,
          negative: 0
        }
      },
      technicalData: {
        indicators: {
          RSI: { value: 0, signal: 'neutral' },
          MACD: { value: 0, signal_line: 0, histogram: 0, signal: 'neutral' },
          ATR: { value: 0 },
          Bollinger_Bands: { upper: 0, middle: 0, lower: 0, signal: 'neutral' },
          Volume_Ratio: { value: 0 },
          Momentum: { value: 0 }
        }
      },
      meanReversionData: {
        trading_opportunities: []
      },
      dailyChart: null,
      minute5Chart: null,
      minute15Chart: null,
      minute60Chart: null,
      newsChart: null,
      queryForm: {
        symbol: ''
      },
      mockSymbols: [],
      loading: false,
      errorMessage: '',
      predictionType: 'daily',
      predictionAccuracies: {
        daily: {
          total: 0,
          direction: 0,
          rmse: 0,
          mae: 0,
          r2: 0,
          relative_error: 0,
          bias: 0
        },
        minute_5: {
          total: 0,
          direction: 0,
          rmse: 0,
          mae: 0,
          r2: 0,
          relative_error: 0,
          bias: 0
        },
        minute_15: {
          total: 0,
          direction: 0,
          rmse: 0,
          mae: 0,
          r2: 0,
          relative_error: 0,
          bias: 0
        },
        minute_60: {
          total: 0,
          direction: 0,
          rmse: 0,
          mae: 0,
          r2: 0,
          relative_error: 0,
          bias: 0
        }
      },
      chartInterval: 0.1,
      chartResizeTimer: null
    }
  },
  mounted() {
    this.loadStockList()
    this.$nextTick(() => {
      this.initCharts()
      window.addEventListener('resize', this.handleResize)
    })
  },
  methods: {
    fetchSuggestions(queryString, cb) {
      if (!Array.isArray(this.mockSymbols)) {
        cb([])
        return
      }

      const results = queryString
        ? this.mockSymbols.filter(item => {
            if (!item || typeof item !== 'object') return false

            const symbol = String(item.symbol || '')
            const name = String(item.name || '')
            const query = String(queryString || '').toLowerCase()

            return symbol.toLowerCase().includes(query) ||
                   name.toLowerCase().includes(query)
          })
        : this.mockSymbols

      cb(results)
    },
    handleSelectSymbol(item) {
      this.queryForm.symbol = item.symbol
    },
    initCharts() {
      try {
        this.$nextTick(() => {
          if (this.$refs.dailyChart) {
            this.dailyChart = echarts.init(this.$refs.dailyChart)
          }
          if (this.$refs.minute5Chart) {
            this.minute5Chart = echarts.init(this.$refs.minute5Chart)
          }
          if (this.$refs.minute15Chart) {
            this.minute15Chart = echarts.init(this.$refs.minute15Chart)
          }
          if (this.$refs.minute60Chart) {
            this.minute60Chart = echarts.init(this.$refs.minute60Chart)
          }
          if (this.$refs.newsChart) {
            this.newsChart = echarts.init(this.$refs.newsChart)
          }
        })
      } catch (error) {
        console.error('图表初始化失败:', error)
      }
    },
    handleResize() {
      if (this.chartResizeTimer) {
        clearTimeout(this.chartResizeTimer)
      }
      this.chartResizeTimer = setTimeout(() => {
        this.resizeCharts()
      }, 100)
    },
    resizeCharts() {
      const charts = [this.dailyChart, this.minute5Chart, this.minute15Chart, this.minute60Chart, this.newsChart]
      charts.forEach(chart => {
        if (chart) {
          chart.resize()
        }
      })
    },
    async refreshSentimentAnalysis(symbol) {
      try {
        const response = await getSentimentAnalysis({ symbol })
        if (response.code === 200) {
          this.sentimentData = response.data
        } else {
          throw new Error(response.msg || '获取市场情绪分析数据失败')
        }
      } catch (error) {
        console.error('获取市场情绪分析数据失败:', error)
        if (error.message && error.message.includes('are in the [columns]')) {
          this.$message.warning('该股票数据不完整，无法进行市场情绪分析')
          this.sentimentData = {
            sentiment_score: 0,
            market_trend: 'neutral',
            confidence: 0
          }
        } else {
          this.$message.error(error.message || '获取市场情绪分析数据失败，请稍后重试')
        }
      }
    },
    async refreshMarketPrediction(symbol) {
      try {
        const response = await getMarketPrediction({ symbol })

        if (response.code === 200) {
          if (response.data.error) {
            if (response.data.error.includes('数据量不足')) {
              this.$message({
                message: '该股票历史数据不足，无法进行预测分析。建议选择上市时间超过6个月的股票。',
                type: 'warning',
                duration: 5000,
                showClose: true
              })
            } else {
              this.$message.error(`获取预测数据失败: ${response.data.error}`)
            }
            this.resetPredictionData()
            return
          }

          const isEmptyData = !response.data.historical ||
                            !response.data.historical.dates ||
                            response.data.historical.dates.length === 0

          if (isEmptyData) {
            this.$message.warning('该股票暂无预测数据，请稍后再试')
            this.resetPredictionData()
            return
          }

          const processedData = this.processPredictionData(response.data)
          this.predictionData = processedData
          this.updatePredictionChart()
        } else {
          throw new Error(response.msg || '获取市场预测数据失败')
        }
      } catch (error) {
        this.$message.error(error.message || '获取市场预测数据失败，请稍后重试')
        this.resetPredictionData()
      }
    },
    processPredictionData(data) {
      const processedData = {
        daily: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_5: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_15: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_60: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        }
      }

      if (data.historical) {
        const isValidHistoricalData = data.historical.dates &&
                                    data.historical.predictions &&
                                    data.historical.actual_prices &&
                                    Array.isArray(data.historical.dates) &&
                                    Array.isArray(data.historical.predictions) &&
                                    Array.isArray(data.historical.actual_prices) &&
                                    data.historical.dates.length > 0 &&
                                    data.historical.predictions.length > 0 &&
                                    data.historical.actual_prices.length > 0;

        if (isValidHistoricalData) {
          processedData.daily = {
            dates: [...data.historical.dates],
            predictions: [...data.historical.predictions],
            actual_prices: [...data.historical.actual_prices],
            future_dates: [],
            future_predictions: []
          }
        }

        if (data.future && data.future.confidence) {
          const accuracy = data.future.confidence
          this.predictionAccuracies.daily = {
            total: typeof accuracy.accuracy === 'number' ? accuracy.accuracy : 0,
            direction: typeof accuracy.direction_accuracy === 'number' ? accuracy.direction_accuracy : 0,
            rmse: typeof accuracy.rmse === 'number' ? accuracy.rmse : 0,
            mae: typeof accuracy.mae === 'number' ? accuracy.mae : 0,
            r2: typeof accuracy.r2 === 'number' ? accuracy.r2 : 0,
            relative_error: typeof accuracy.relative_error === 'number' ? accuracy.relative_error : 0,
            bias: typeof accuracy.bias === 'number' ? accuracy.bias : 0
          }
        }
      }

      if (data.future) {
        processedData.daily = {
          ...processedData.daily,
          future_dates: Array.isArray(data.future.dates) ? [...data.future.dates] : [],
          future_predictions: Array.isArray(data.future.predictions) ? [...data.future.predictions] : []
        }
      }

      const minuteTypes = ['minute_5', 'minute_15', 'minute_60']
      minuteTypes.forEach(type => {
        if (data[type]) {
          if (data[type].historical) {
            processedData[type] = {
              ...processedData[type],
              dates: Array.isArray(data[type].historical.dates) ? [...data[type].historical.dates] : [],
              predictions: Array.isArray(data[type].historical.predictions) ? [...data[type].historical.predictions] : [],
              actual_prices: Array.isArray(data[type].historical.actual_prices) ? [...data[type].historical.actual_prices] : []
            }
          }

          if (data[type].future) {
            processedData[type] = {
              ...processedData[type],
              future_dates: Array.isArray(data[type].future.dates) ? [...data[type].future.dates] : [],
              future_predictions: Array.isArray(data[type].future.predictions) ? [...data[type].future.predictions] : []
            }

            if (data[type].future.confidence) {
              const accuracy = data[type].future.confidence
              this.predictionAccuracies[type] = {
                total: typeof accuracy.accuracy === 'number' ? accuracy.accuracy : 0,
                direction: typeof accuracy.direction_accuracy === 'number' ? accuracy.direction_accuracy : 0,
                rmse: typeof accuracy.rmse === 'number' ? accuracy.rmse : 0,
                mae: typeof accuracy.mae === 'number' ? accuracy.mae : 0,
                r2: typeof accuracy.r2 === 'number' ? accuracy.r2 : 0,
                relative_error: typeof accuracy.relative_error === 'number' ? accuracy.relative_error : 0,
                bias: typeof accuracy.bias === 'number' ? accuracy.bias : 0
              }
            }
          }
        }
      })

      return processedData
    },
    resetPredictionData() {
      this.predictionData = {
        predictions: [],
        actual_prices: [],
        accuracy: 0,
        daily: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_5: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_15: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        },
        minute_60: {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        }
      }

      this.predictionAccuracies = {
        daily: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_5: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_15: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_60: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 }
      }

      this.updatePredictionChart()
    },
    updatePredictionChart() {
      const types = ['daily', 'minute_5', 'minute_15', 'minute_60']
      const charts = {
        'daily': this.dailyChart,
        'minute_5': this.minute5Chart,
        'minute_15': this.minute15Chart,
        'minute_60': this.minute60Chart
      }

      types.forEach(type => {
        const currentData = this.predictionData[type] || {
          dates: [],
          predictions: [],
          actual_prices: [],
          future_dates: [],
          future_predictions: []
        }

        const hasValidData = currentData &&
                           Array.isArray(currentData.dates) &&
                           Array.isArray(currentData.predictions) &&
                           Array.isArray(currentData.actual_prices) &&
                           currentData.dates.length > 0 &&
                           currentData.predictions.length > 0 &&
                           currentData.actual_prices.length > 0;

        if (!hasValidData) {
          this.setEmptyChart(charts[type], type)
          return
        }

        const allDates = [...(currentData.dates || []), ...(currentData.future_dates || [])]
        const allPredictions = [...(currentData.predictions || []), ...(currentData.future_predictions || [])]
        const allActualPrices = [...(currentData.actual_prices || [])]

        if (allDates.length === 0 || allPredictions.length === 0) {
          this.setEmptyChart(charts[type], type)
          return
        }

        const validDates = allDates
        const validPredictions = allPredictions
        const validActualPrices = allActualPrices

        const allPrices = [...validPredictions, ...validActualPrices].filter(v => v !== null && !isNaN(v))
        if (allPrices.length === 0) {
          this.setEmptyChart(charts[type], type)
          return
        }

        const minPrice = Math.min(...allPrices)
        const maxPrice = Math.max(...allPrices)
        const priceRange = maxPrice - minPrice
        const padding = priceRange * 0.1

        const option = {
          title: {
            text: `${this.getChartTitle(type)}预测分析`,
            left: 'center'
          },
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              const date = params[0].axisValue
              let result = `${date}<br/>`
              params.forEach(param => {
                if (param.value !== null && !isNaN(param.value) && typeof param.value === 'number') {
                  const value = param.value
                  const color = param.color
                  const marker = `<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>`
                  result += `${marker}${param.seriesName}: ${value.toFixed(2)}<br/>`
                }
              })
              return result
            }
          },
          legend: {
            data: ['预测价格', '实际价格'],
            bottom: 0
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            data: validDates,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax',
            axisPointer: {
              z: 100
            },
            axisLabel: {
              rotate: 45,
              formatter: function(value) {
                if (!value) return '';
                if (type === 'daily') {
                  return value.substring(5);
                }
                return value.substring(11);
              }
            }
          },
          yAxis: {
            type: 'value',
            scale: true,
            splitNumber: 2,
            axisLine: { lineStyle: { color: '#dcdfe6' } },
            axisLabel: { color: '#666' },
            splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
            min: Math.floor((minPrice - padding) / this.chartInterval) * this.chartInterval,
            max: Math.ceil((maxPrice + padding) / this.chartInterval) * this.chartInterval,
            interval: this.chartInterval
          },
          dataZoom: [{
            type: 'inside',
            start: 0,
            end: 100
          }, {
            show: true,
            type: 'slider',
            bottom: '0%',
            start: 0,
            end: 100
          }],
          series: [
            {
              name: '预测价格',
              type: 'line',
              data: validPredictions,
              smooth: true,
              showSymbol: false,
              lineStyle: {
                width: 2,
                color: '#409EFF'
              },
              itemStyle: {
                color: '#409EFF'
              },
              markPoint: {
                data: [
                  { type: 'max', name: '最大值' },
                  { type: 'min', name: '最小值' }
                ]
              },
              connectNulls: true
            },
            {
              name: '实际价格',
              type: 'line',
              data: validActualPrices,
              smooth: true,
              showSymbol: false,
              lineStyle: {
                width: 2,
                color: '#67C23A'
              },
              itemStyle: {
                color: '#67C23A'
              },
              connectNulls: true
            }
          ]
        }

        if (charts[type]) {
          charts[type].setOption(option, true)
        }
      })
    },
    setEmptyChart(chart, type) {
      if (!chart) return;

      const option = {
        title: {
          text: `${this.getChartTitle(type)}预测分析`,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          interval: this.chartInterval
        },
        series: [],
        graphic: [{
          type: 'text',
          left: 'center',
          top: 'middle',
          style: {
            text: '暂无数据',
            fontSize: 20,
            fill: '#999'
          }
        }]
      }
      chart.setOption(option)
    },
    async refreshNewsAnalysis(symbol) {
      try {
        console.log('开始获取新闻分析数据，股票代码:', symbol)
        const response = await getNewsAnalysis({ symbol })
        console.log('新闻分析API响应:', response)

        if (response.code === 200) {
          console.log('新闻分析数据获取成功:', response.data)
          this.newsData = response.data

          // 打印新闻列表详情
          if (response.data.news_list && Array.isArray(response.data.news_list)) {
            console.log('新闻数量:', response.data.news_list.length)
            response.data.news_list.forEach((news, index) => {
              console.log(`新闻 #${index + 1}:`, {
                标题: news.title,
                情感: news.sentiment,
                发布时间: news.publish_time
              })
            })
          } else {
            console.warn('未找到新闻列表数据或数据格式不正确')
          }

          // 打印情感分布详情
          if (response.data.sentiment_distribution) {
            console.log('情感分布详情:', {
              积极: response.data.sentiment_distribution.positive,
              中性: response.data.sentiment_distribution.neutral,
              消极: response.data.sentiment_distribution.negative
            })
          } else {
            console.warn('未找到情感分布数据')
          }

          this.updateNewsChart()
        } else {
          console.error('新闻分析数据获取失败:', response.msg)
          throw new Error(response.msg || '获取新闻分析数据失败')
        }
      } catch (error) {
        console.error('获取新闻分析数据失败:', error)
        this.$message.error('获取新闻分析数据失败，请稍后重试')
      }
    },
    async refreshTechnicalIndicators(symbol) {
      try {
        const response = await getTechnicalIndicators({ symbol })
        if (response.code === 200) {
          this.technicalData = response.data
        }
      } catch (error) {
        console.error('获取技术指标分析数据失败:', error)
      }
    },
    async refreshMeanReversion(symbol) {
      try {
        console.log('开始获取均值回归分析数据，股票代码:', symbol)
        const response = await getMeanReversionAnalysis({ symbol })
        console.log('均值回归分析API响应:', response)

        if (response.code === 200) {
          console.log('均值回归分析数据获取成功:', response.data)
          this.meanReversionData = response.data

          // 打印交易机会详情
          if (response.data.trading_opportunities && Array.isArray(response.data.trading_opportunities)) {
            console.log('交易机会数量:', response.data.trading_opportunities.length)
            response.data.trading_opportunities.forEach((opportunity, index) => {
              console.log(`交易机会 #${index + 1}:`, {
                日期: opportunity.date,
                信号: opportunity.signal,
                买入价格: opportunity.buy_price,
                卖出价格: opportunity.sell_price,
                预期收益: opportunity.expected_return,
                收益率: opportunity.return_rate
              })
            })
          } else {
            console.warn('未找到交易机会数据或数据格式不正确')
          }
        } else {
          console.error('均值回归分析数据获取失败:', response.msg)
          throw new Error(response.msg || '获取均值回归分析数据失败')
        }
      } catch (error) {
        console.error('获取均值回归分析数据失败:', error)
        this.$message.error('获取均值回归分析数据失败，请稍后重试')
      }
    },
    updateNewsChart() {
      const option = {
        title: {
          text: '新闻情感分布',
          left: 'center'
        },
        tooltip: {
          trigger: 'item'
        },
        legend: {
          orient: 'vertical',
          left: 'left'
        },
        series: [
          {
            type: 'pie',
            radius: '50%',
            data: [
              { value: this.newsData.sentiment_distribution.positive, name: '积极' },
              { value: this.newsData.sentiment_distribution.neutral, name: '中性' },
              { value: this.newsData.sentiment_distribution.negative, name: '消极' }
            ],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      }
      this.newsChart.setOption(option)
    },
    getSentimentClass(score) {
      if (score >= 60) return 'positive'
      if (score <= 40) return 'negative'
      return 'neutral'
    },
    getTrendClass(trend) {
      return trend
    },
    getTrendText(trend) {
      const trendMap = {
        bullish: '看涨',
        bearish: '看跌',
        neutral: '中性'
      }
      return trendMap[trend] || '未知'
    },
    getIndicatorClass(signal) {
      const classMap = {
        overbought: 'negative',
        oversold: 'positive',
        bullish: 'positive',
        bearish: 'negative',
        neutral: 'neutral'
      }
      return classMap[signal] || 'neutral'
    },
    getSignalText(signal) {
      const signalMap = {
        overbought: '超买',
        oversold: '超卖',
        bullish: '看涨',
        bearish: '看跌',
        neutral: '中性'
      }
      return signalMap[signal] || '未知'
    },
    getBBValue(bb) {
      if (!bb || typeof bb.upper === 'undefined') {
        return '-'
      }
      return `${bb.upper.toFixed(2)} / ${bb.middle.toFixed(2)} / ${bb.lower.toFixed(2)}`
    },
    getMACDValue(macd) {
      if (!macd || typeof macd.value === 'undefined') {
        return '-'
      }
      const macdValue = typeof macd.value === 'number' ? macd.value.toFixed(2) : '-'
      const signalValue = typeof macd.signal_line === 'number' ? macd.signal_line.toFixed(2) : '-'
      const histogramValue = typeof macd.histogram === 'number' ? macd.histogram.toFixed(2) : '-'

      return `${macdValue} / ${signalValue} / ${histogramValue}`
    },
    getVolumeRatioClass(volumeRatio) {
      if (!volumeRatio || typeof volumeRatio.value !== 'number') return 'neutral'
      if (volumeRatio.value > 1) return 'positive'
      return 'negative'
    },
    getMomentumClass(momentum) {
      if (!momentum || typeof momentum.value !== 'number') return 'neutral'
      if (momentum.value > 0) return 'positive'
      return 'negative'
    },
    getNewsSentimentType(sentiment) {
      const typeMap = {
        positive: 'success',
        neutral: 'info',
        negative: 'danger'
      }
      return typeMap[sentiment] || 'info'
    },
    getNewsSentimentText(sentiment) {
      const textMap = {
        positive: '积极',
        neutral: '中性',
        negative: '消极'
      }
      return textMap[sentiment] || '未知'
    },
    async loadStockList() {
      const maxRetries = 3;
      let retryCount = 0;

      const tryLoadStockList = async () => {
        try {
          const response = await getstocklist();
          if (response.code === 200 && Array.isArray(response.data)) {
            this.mockSymbols = response.data.map(item => ({
              ...item,
              value: item.symbol
            }));
          } else {
            this.mockSymbols = [];
            this.$message.warning('股票列表数据格式不正确，请稍后重试');
          }
        } catch (error) {
          if (retryCount < maxRetries - 1) {
            retryCount++;
            this.$message.warning(`股票列表加载失败，正在进行第${retryCount + 1}次重试...`);
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount)));
            return tryLoadStockList();
          } else {
            this.mockSymbols = [];
            this.$message.error('股票列表加载失败，请检查网络连接后重试');
          }
        }
      };

      await tryLoadStockList();
    },
    handleSymbolInput(val) {
      if (!val) return
      if (val.length > 6) {
        this.queryForm.symbol = val.slice(0, 6)
      }
    },
    async refreshAllData() {
      if (!this.queryForm.symbol || !/^\d{6}$/.test(this.queryForm.symbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return
      }
      this.loading = true
      this.errorMessage = ''

      // 重置所有数据
      this.resetAllData()

      try {
        await Promise.all([
          this.refreshSentimentAnalysis(this.queryForm.symbol),
          this.refreshMarketPrediction(this.queryForm.symbol),
          this.refreshNewsAnalysis(this.queryForm.symbol),
          this.refreshTechnicalIndicators(this.queryForm.symbol),
          this.refreshMeanReversion(this.queryForm.symbol)
        ])
      } catch (error) {
        console.error('数据刷新失败:', error)
        if (error.message && error.message.includes('数据量不足')) {
          this.$message.warning('该股票历史数据不足，请选择上市时间超过一年的股票')
        } else {
          this.$message.error('数据刷新失败，请稍后重试')
        }
      } finally {
        this.loading = false
      }
    },
    resetAllData() {
      this.sentimentData = {
        sentiment_score: 0,
        market_trend: 'neutral',
        confidence: 0
      }
      this.predictionData = {
        predictions: [],
        actual_prices: [],
        accuracy: 0,
        daily: {},
        minute_5: {},
        minute_15: {},
        minute_60: {}
      }
      this.newsData = {
        news_list: [],
        sentiment_distribution: {
          positive: 0,
          neutral: 0,
          negative: 0
        }
      }
      this.technicalData = {
        indicators: {
          RSI: { value: 0, signal: 'neutral' },
          MACD: { value: 0, signal_line: 0, histogram: 0, signal: 'neutral' },
          ATR: { value: 0 },
          Bollinger_Bands: { upper: 0, middle: 0, lower: 0, signal: 'neutral' },
          Volume_Ratio: { value: 0 },
          Momentum: { value: 0 }
        }
      }
      this.meanReversionData = {
        trading_opportunities: []
      }
      this.predictionAccuracies = {
        daily: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_5: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_15: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 },
        minute_60: { total: 0, direction: 0, rmse: 0, mae: 0, r2: 0, relative_error: 0, bias: 0 }
      }

      this.updatePredictionChart()
      this.updateNewsChart()
    },
    formatDate(dateStr) {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      if (isNaN(date.getTime())) return dateStr
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).replace(/\//g, '-')
    },
    formatDateTime(dateTimeStr) {
      if (!dateTimeStr) return '-'
      const date = new Date(dateTimeStr)
      if (isNaN(date.getTime())) return dateTimeStr
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).replace(/\//g, '-')
    },
    getProfitClass(value) {
      if (!value || typeof value !== 'number') return ''
      return value > 0 ? 'positive' : 'negative'
    },
    getChartTitle(type) {
      const titleMap = {
        'daily': '日线',
        'minute_5': '5分钟',
        'minute_15': '15分钟',
        'minute_60': '1小时'
      }
      return titleMap[type] || type
    },
    getAccuracyClass(accuracy) {
      if (accuracy === null || accuracy === undefined || typeof accuracy !== 'number') {
        return 'low-accuracy'
      }
      // 确保准确率不超过100%
      const normalizedAccuracy = Math.min(accuracy, 100)
      if (normalizedAccuracy >= 70) {
        return 'high-accuracy'
      }
      if (normalizedAccuracy >= 50) {
        return 'medium-accuracy'
      }
      return 'low-accuracy'
    },
    getRMSEClass(rmse) {
      if (rmse === undefined || rmse === null || isNaN(rmse)) {
        return 'low-accuracy'
      }
      if (rmse < 0.1) {
        return 'high-accuracy'
      }
      if (rmse < 0.2) {
        return 'medium-accuracy'
      }
      return 'low-accuracy'
    },
    getR2Class(r2) {
      if (r2 === undefined || r2 === null || isNaN(r2)) {
        return 'low-accuracy'
      }
      if (r2 >= 0.8) {
        return 'high-accuracy'
      }
      if (r2 >= 0.6) {
        return 'medium-accuracy'
      }
      return 'low-accuracy'
    },
    getErrorClass(error) {
      if (error === undefined || error === null || isNaN(error)) {
        return 'low-accuracy'
      }
      if (error <= 0.05) {
        return 'high-accuracy'
      }
      if (error <= 0.1) {
        return 'medium-accuracy'
      }
      return 'low-accuracy'
    },
    getBiasClass(bias) {
      if (bias === undefined || bias === null || isNaN(bias)) {
        return 'low-accuracy'
      }
      if (Math.abs(bias) <= 0.02) {
        return 'high-accuracy'
      }
      if (Math.abs(bias) <= 0.05) {
        return 'medium-accuracy'
      }
      return 'low-accuracy'
    },
    formatValue(value) {
      if (value === null || value === undefined || isNaN(value)) return '0.00'
      return value.toFixed(2)
    }
  },
  computed: {
    sortedTradingOpportunities: {
      get() {
        if (!this.meanReversionData.trading_opportunities) {
          return []
        }
        return [...this.meanReversionData.trading_opportunities].sort((a, b) => {
          return new Date(b.date) - new Date(a.date)
        })
      }
    },
    formattedPredictionAccuracies() {
      const formatValue = (value) => {
        if (value === null || value === undefined || isNaN(value) || typeof value !== 'number') return '0.00%'
        return value.toFixed(2) + '%'
      }

      const formatError = (value) => {
        if (value === null || value === undefined || isNaN(value) || typeof value !== 'number') return '0.0000'
        return value.toFixed(4)
      }

      const formatBias = (value) => {
        if (value === null || value === undefined || isNaN(value) || typeof value !== 'number') return '0.00%'
        return value.toFixed(2) + '%'
      }

      const formatAccuracy = (type) => {
        const accuracy = this.predictionAccuracies[type] || {}
        return {
          total: formatValue(accuracy.total),
          direction: formatValue(accuracy.direction),
          rmse: formatError(accuracy.rmse),
          mae: formatError(accuracy.mae),
          r2: formatError(accuracy.r2),
          relative_error: formatValue(accuracy.relative_error),
          bias: formatBias(accuracy.bias)
        }
      }

      return {
        daily: formatAccuracy('daily'),
        minute_5: formatAccuracy('minute_5'),
        minute_15: formatAccuracy('minute_15'),
        minute_60: formatAccuracy('minute_60')
      }
    }
  },
  watch: {
    predictionType() {
      this.updatePredictionChart()
    }
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
    if (this.chartResizeTimer) {
      clearTimeout(this.chartResizeTimer)
    }
    const charts = [this.dailyChart, this.minute5Chart, this.minute15Chart, this.minute60Chart, this.newsChart]
    charts.forEach(chart => {
      if (chart) {
        chart.dispose()
      }
    })
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  padding: 20px;

  .box-card {
    margin-bottom: 20px;
  }

  .sentiment-analysis {
    .sentiment-score,
    .market-trend,
    .confidence {
      text-align: center;
      padding: 15px;
      height: 120px;
      display: flex;
      flex-direction: column;
      justify-content: center;

      .score-title,
      .trend-title,
      .confidence-title {
        font-size: 14px;
        color: #606266;
        margin-bottom: 12px;
      }

      .score-value,
      .trend-value,
      .confidence-value {
        font-size: 24px;
        font-weight: bold;
      }
    }
  }

  .technical-indicators {
    .indicator-item {
      text-align: center;
      padding: 15px;
      height: 120px;
      display: flex;
      flex-direction: column;
      justify-content: center;

      .indicator-title {
        font-size: 14px;
        color: #606266;
        margin-bottom: 12px;
      }

      .indicator-value {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 12px;
      }

      .indicator-signal {
        font-size: 13px;
        color: #909399;
      }
    }
  }

  .news-analysis {
    .sentiment-distribution {
      margin-bottom: 20px;
    }

    .news-list {
      margin-top: 20px;
    }
  }

  .mean-reversion {
    .trading-opportunities {
      .opportunities-title {
        font-size: 16px;
        color: #606266;
        margin-bottom: 15px;
      }
    }
  }

  .positive {
    color: #67C23A;
  }

  .negative {
    color: #F56C6C;
  }

  .neutral {
    color: #909399;
  }

  .bullish {
    color: #67C23A;
  }

  .bearish {
    color: #F56C6C;
  }

  .news-title {
    font-size: 14px;
    color: #303133;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .prediction-charts {
    .prediction-accuracy {
      margin-bottom: 30px;

      .accuracy-title {
        font-size: 18px;
        color: #303133;
        margin-bottom: 20px;
        text-align: center;
      }

      .accuracy-item {
        text-align: center;
        padding: 20px;
        background: #f5f7fa;
        border-radius: 4px;

        .accuracy-label {
          font-size: 16px;
          color: #303133;
          margin-bottom: 15px;
          font-weight: bold;
        }

        .accuracy-metrics {
          .metric-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding: 6px 0;

            .metric-label {
              font-size: 14px;
              color: #606266;
            }

            .metric-value {
              font-size: 15px;
              font-weight: bold;

              &.high-accuracy {
                color: #67C23A;
              }

              &.medium-accuracy {
                color: #E6A23C;
              }

              &.low-accuracy {
                color: #F56C6C;
              }
            }
          }
        }
      }
    }

    .chart-item {
      background: #fff;
      border-radius: 4px;
      padding: 20px;
      margin-bottom: 20px;

      .chart-title {
        font-size: 18px;
        color: #303133;
        margin-bottom: 20px;
        text-align: center;
      }

      .chart-container {
        width: 100%;
        height: 400px;
        min-height: 400px;
      }
    }
  }
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
</style>

