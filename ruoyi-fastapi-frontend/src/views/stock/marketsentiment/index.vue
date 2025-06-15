<template>
  <div class="app-container">
    <el-card class="box-card">
      <div slot="header" class="clearfix">
        <span>市场情绪分析</span>
        <el-button style="float: right; padding: 3px 0" type="text" @click="refreshData">刷新</el-button>
      </div>
      
      <!-- 市场情绪概览 -->
      <el-row :gutter="20" class="sentiment-overview">
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="sentiment-card">
              <div class="sentiment-title">市场情绪指数</div>
              <div class="sentiment-value" :class="sentimentClass">
                {{ marketSentiment.sentiment || '中性' }}
              </div>
              <div class="sentiment-score">得分: {{ marketSentiment.sentiment_score }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="sentiment-card">
              <div class="sentiment-title">更新时间</div>
              <div class="sentiment-value">{{ marketSentiment.analysis_time }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="sentiment-card">
              <div class="sentiment-title">预测准确率</div>
              <div class="sentiment-value">{{ (predictionAccuracy * 100).toFixed(2) }}%</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 股票预测 -->
      <el-card class="prediction-card">
        <div slot="header" class="clearfix">
          <span>股票预测</span>
          <el-button style="float: right; padding: 3px 0" type="text" @click="showPredictionDialog">新增预测</el-button>
        </div>
        
        <el-table :data="predictions" style="width: 100%">
          <el-table-column prop="stock_code" label="股票代码" width="120"></el-table-column>
          <el-table-column prop="last_price" label="当前价格" width="120">
            <template slot-scope="scope">
              {{ scope.row.last_price.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="预测价格" width="180">
            <template slot-scope="scope">
              <div v-for="(price, index) in scope.row.predictions" :key="index">
                {{ price.toFixed(2) }}
                <span :class="getPriceChangeClass(scope.row.price_changes[index])">
                  ({{ scope.row.price_changes[index].toFixed(2) }}%)
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="预测日期" width="180">
            <template slot-scope="scope">
              <div v-for="date in scope.row.dates" :key="date">
                {{ date }}
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template slot-scope="scope">
              <el-button type="text" @click="showPredictionChart(scope.row)">查看图表</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 预测对话框 -->
      <el-dialog title="股票预测" :visible.sync="predictionDialogVisible" width="30%">
        <el-form :model="predictionForm" label-width="100px">
          <el-form-item label="股票代码">
            <el-input v-model="predictionForm.stock_code" placeholder="请输入股票代码"></el-input>
          </el-form-item>
          <el-form-item label="预测天数">
            <el-input-number v-model="predictionForm.days" :min="1" :max="30"></el-input-number>
          </el-form-item>
        </el-form>
        <span slot="footer" class="dialog-footer">
          <el-button @click="predictionDialogVisible = false">取 消</el-button>
          <el-button type="primary" @click="predictStock">预 测</el-button>
        </span>
      </el-dialog>

      <!-- 预测图表对话框 -->
      <el-dialog title="预测趋势图" :visible.sync="chartDialogVisible" width="70%">
        <div ref="predictionChart" style="width: 100%; height: 400px;"></div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getMarketSentiment, predictStockPrice } from '@/api/market/sentiment'

export default {
  name: 'MarketSentiment',
  data() {
    return {
      marketSentiment: {
        sentiment: '中性',
        sentiment_score: 0,
        analysis_time: ''
      },
      predictions: [],
      predictionAccuracy: 0,
      predictionDialogVisible: false,
      chartDialogVisible: false,
      predictionForm: {
        stock_code: '',
        days: 5
      },
      currentChart: null
    }
  },
  computed: {
    sentimentClass() {
      const score = this.marketSentiment.sentiment_score
      if (score > 0) return 'positive'
      if (score < 0) return 'negative'
      return 'neutral'
    }
  },
  created() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      try {
        const response = await getMarketSentiment()
        if (response.code === 200) {
          this.marketSentiment = response.data
        }
      } catch (error) {
        console.error('获取市场情绪数据失败:', error)
        this.$message.error('获取市场情绪数据失败')
      }
    },
    async predictStock() {
      try {
        const response = await predictStockPrice({
          stock_code: this.predictionForm.stock_code,
          days: this.predictionForm.days
        })
        if (response.code === 200) {
          this.predictions.unshift(response.data)
          this.predictionDialogVisible = false
          this.$message.success('预测成功')
        }
      } catch (error) {
        console.error('预测失败:', error)
        this.$message.error('预测失败')
      }
    },
    showPredictionDialog() {
      this.predictionForm = {
        stock_code: '',
        days: 5
      }
      this.predictionDialogVisible = true
    },
    showPredictionChart(row) {
      this.chartDialogVisible = true
      this.$nextTick(() => {
        this.initChart(row)
      })
    },
    initChart(data) {
      if (this.currentChart) {
        this.currentChart.dispose()
      }
      
      const chartDom = this.$refs.predictionChart
      this.currentChart = echarts.init(chartDom)
      
      const option = {
        title: {
          text: `${data.stock_code} 价格预测`
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: data.dates
        },
        yAxis: {
          type: 'value',
          name: '价格'
        },
        series: [
          {
            name: '预测价格',
            type: 'line',
            data: data.predictions,
            markPoint: {
              data: [
                { type: 'max', name: '最大值' },
                { type: 'min', name: '最小值' }
              ]
            }
          }
        ]
      }
      
      this.currentChart.setOption(option)
    },
    getPriceChangeClass(change) {
      if (change > 0) return 'price-up'
      if (change < 0) return 'price-down'
      return ''
    },
    refreshData() {
      this.fetchData()
    }
  }
}
</script>

<style lang="scss" scoped>
.sentiment-overview {
  margin-bottom: 20px;
}

.sentiment-card {
  text-align: center;
  padding: 20px;
  
  .sentiment-title {
    font-size: 16px;
    color: #606266;
    margin-bottom: 10px;
  }
  
  .sentiment-value {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 10px;
    
    &.positive {
      color: #67C23A;
    }
    
    &.negative {
      color: #F56C6C;
    }
    
    &.neutral {
      color: #909399;
    }
  }
  
  .sentiment-score {
    font-size: 14px;
    color: #909399;
  }
}

.prediction-card {
  margin-top: 20px;
}

.price-up {
  color: #67C23A;
}

.price-down {
  color: #F56C6C;
}
</style> 