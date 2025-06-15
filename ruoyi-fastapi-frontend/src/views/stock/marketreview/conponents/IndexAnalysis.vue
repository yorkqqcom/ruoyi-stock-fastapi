<template>
  <el-card class="box-card" v-loading="loading.indexData">
    <div slot="header" class="clearfix">
      <span>指数分析</span>
    </div>
    <el-row :gutter="20">
      <el-col :span="8" v-for="(index, key) in indexData.cards" :key="key">
        <div class="index-card" :class="{'up': index.change > 0, 'down': index.change < 0}">
          <div class="index-header">
            <span class="index-name">{{ index.name || '--' }}</span>
            <span class="index-date">{{ index.date || '--' }}</span>
          </div>
          <div class="index-main">
            <div class="index-value">{{ formatValue(index.value) }}</div>
            <div class="index-change">
              <span class="change-value">{{ formatChange(index.change) }}</span>
            </div>
          </div>
          <div class="index-metrics">
            <div class="metrics-grid">
              <div class="metric-item">
                <span class="label">MA5</span>
                <span class="value">{{ formatValue(index.ma5) }}</span>
              </div>
              <div class="metric-item">
                <span class="label">MA10</span>
                <span class="value">{{ formatValue(index.ma10) }}</span>
              </div>
              <div class="metric-item">
                <span class="label">MA20</span>
                <span class="value">{{ formatValue(index.ma20) }}</span>
              </div>
              <div class="metric-item">
                <span class="label">成交量</span>
                <span class="value">{{ formatVolume(index.volume) }}</span>
              </div>
              <div class="metric-item">
                <span class="label">成交额</span>
                <span class="value">{{ formatAmount(index.amount) }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
    <!-- 修改图表布局为并排显示 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <div class="chart-container" ref="indexChart" v-loading="loading.indexChart"></div>
      </el-col>
      <el-col :span="12">
        <div class="min-chart-container" ref="minChart" v-loading="loading.minChart"></div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script>
import * as echarts from 'echarts'
import { getIndexData, getMainIndicesMinData } from '@/api/stock/market'

export default {
  name: 'IndexAnalysis',
  data() {
    return {
      loading: {
        indexData: false,
        indexChart: false,
        minChart: false
      },
      indexData: {
        cards: [],
        chart: {
          dates: [],
          shValue: [],
          szValue: [],
          cybValue: []
        }
      },
      minData: {
        sh: {
          times: [],
          prices: [],
          volumes: [],
          amounts: []
        },
        sz: {
          times: [],
          prices: [],
          volumes: [],
          amounts: []
        },
        cyb: {
          times: [],
          prices: [],
          amounts: []
        }
      },
      indexChart: null,
      minChart: null
    }
  },
  mounted() {
    this.initData()
    // 使用 nextTick 确保 DOM 已经渲染完成
    this.$nextTick(() => {
      this.initCharts()
    })
    // 添加窗口大小变化监听
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    // 移除窗口大小变化监听
    window.removeEventListener('resize', this.handleResize)
    // 销毁图表实例
    if (this.indexChart) {
      this.indexChart.dispose()
    }
    if (this.minChart) {
      this.minChart.dispose()
    }
  },
  methods: {
    // 处理窗口大小变化
    handleResize() {
      if (this.indexChart) {
        this.indexChart.resize()
      }
      if (this.minChart) {
        this.minChart.resize()
      }
    },
    async initData() {
      try {
        // 获取指数数据
        this.loading.indexData = true
        this.loading.indexChart = true
        const indexRes = await getIndexData()
        if (indexRes.code === 200) {
          this.indexData = indexRes.data
          // 使用 nextTick 确保数据更新后再更新图表
          this.$nextTick(() => {
            this.updateIndexChart()
          })
        }
        this.loading.indexData = false
        this.loading.indexChart = false

        // 获取分时数据
        this.loading.minChart = true
        await this.updateMinChart()
        this.loading.minChart = false
      } catch (error) {
        console.error('获取数据失败：', error)
        this.$message.error('获取数据失败')
        // 关闭所有加载状态
        Object.keys(this.loading).forEach(key => {
          this.loading[key] = false
        })
      }
    },
    initCharts() {
      // 确保 DOM 元素存在
      if (this.$refs.indexChart) {
        this.indexChart = echarts.init(this.$refs.indexChart)
        this.updateIndexChart()
      }

      if (this.$refs.minChart) {
        this.minChart = echarts.init(this.$refs.minChart)
        this.updateMinChart()
      }
    },
    updateIndexChart() {
      if (!this.indexChart || !this.indexData.chart || !this.indexData.chart.dates) {
        return
      }

      const series = [];
      const yAxis = [];
      
      // 显示所有指数
      yAxis.push({
        type: 'value',
        position: 'left',
        scale: true,
        splitArea: { show: true },
        axisLabel: { show: false },
        nameTextStyle: { show: false }
      });
      yAxis.push({
        type: 'value',
        position: 'right',
        scale: true,
        splitArea: { show: true },
        axisLabel: { show: false },
        nameTextStyle: { show: false }
      });
      yAxis.push({
        type: 'value',
        position: 'right',
        offset: 80,
        scale: true,
        splitArea: { show: true },
        axisLabel: { show: false },
        nameTextStyle: { show: false }
      });

      series.push({
        name: '上证指数',
        type: 'line',
        yAxisIndex: 0,
        data: this.indexData.chart.shValue,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 }
      });
      series.push({
        name: '深证成指',
        type: 'line',
        yAxisIndex: 1,
        data: this.indexData.chart.szValue,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 }
      });
      series.push({
        name: '创业板指',
        type: 'line',
        yAxisIndex: 2,
        data: this.indexData.chart.cybValue,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 }
      });

      const option = {
        title: {
          text: '历史行情',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: series.map(item => item.name),
          top: 30
        },
        grid: {
          left: '0%',
          right: '0%',
          bottom: '0%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: this.indexData.chart.dates,
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
              return value.substring(5); // 只显示月-日
            }
          }
        },
        yAxis: yAxis,
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
        series: series
      }
      this.indexChart.setOption(option)
    },
    async updateMinChart() {
      if (!this.minChart) {
        return
      }
      try {
        const res = await getMainIndicesMinData({
          period: '1'
        })
        
        if (res.code === 200) {
          this.minData = res.data
          
          const series = [];
          const yAxis = [];
          
          // 显示所有指数
          yAxis.push({
            type: 'value',
            position: 'left',
            scale: true,
            splitArea: { show: true },
            axisLabel: { show: false },
            nameTextStyle: { show: false }
          });
          yAxis.push({
            type: 'value',
            position: 'right',
            scale: true,
            splitArea: { show: true },
            axisLabel: { show: false },
            nameTextStyle: { show: false }
          });
          yAxis.push({
            type: 'value',
            position: 'right',
            offset: 80,
            scale: true,
            splitArea: { show: true },
            axisLabel: { show: false },
            nameTextStyle: { show: false }
          });

          series.push({
            name: '上证指数',
            type: 'line',
            yAxisIndex: 0,
            data: this.minData.sh.prices,
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2 }
          });
          series.push({
            name: '深证成指',
            type: 'line',
            yAxisIndex: 1,
            data: this.minData.sz.prices,
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2 }
          });
          series.push({
            name: '创业板指',
            type: 'line',
            yAxisIndex: 2,
            data: this.minData.cyb.prices,
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2 }
          });
          
          const option = {
            title: {
              text: '分时行情',
              left: 'center'
            },
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'cross'
              }
            },
            legend: {
              data: series.map(item => item.name),
              top: 30
            },
            grid: {
              left: '0%',
              right: '0%',
              bottom: '0%',
              top: '10%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              data: this.minData.sh.times,
              scale: true,
              boundaryGap: false,
              axisLine: { onZero: false },
              splitLine: { show: false },
              min: '09:30',
              max: '15:00',
              axisPointer: {
                z: 100
              },
              axisLabel: {
                formatter: function(value) {
                  // 只显示时间部分，格式为 HH:mm
                  return value.split(' ')[1].substring(0, 5);
                }
              }
            },
            yAxis: yAxis,
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
            series: series
          }
          
          this.minChart.setOption(option)
        }
      } catch (error) {
        console.error('获取分时数据失败：', error)
        this.$message.error('获取分时数据失败')
      }
    },
    // 格式化数值，统一保留2位小数
    formatValue(value) {
      if (value === undefined || value === null) return '--';
      return Number(value).toFixed(2);
    },
    
    // 格式化涨跌幅
    formatChange(change) {
      if (change === undefined || change === null) return '--';
      return (change > 0 ? '+' : '') + Number(change).toFixed(2) + '%';
    },
    
    // 格式化成交量
    formatVolume(volume) {
      if (volume === undefined || volume === null) return '--';
      const value = Number(volume);
      if (value >= 100000000) {
        return (value / 100000000).toFixed(2) + '亿手';
      } else if (value >= 10000) {
        return (value / 10000).toFixed(2) + '万手';
      }
      return value.toFixed(0) + '手';
    },
    
    // 格式化成交金额
    formatAmount(amount) {
      if (amount === undefined || amount === null) return '--';
      const value = Number(amount);
      if (value >= 100000000) {
        return (value / 100000000).toFixed(2) + '亿';
      } else if (value >= 10000) {
        return (value / 10000).toFixed(2) + '万';
      }
      return value.toFixed(2) + '元';
    }
  }
}
</script>

<style lang="scss" scoped>
.index-card {
  padding: 15px;
  border-radius: 4px;
  background-color: #fff;
  margin-bottom: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s;

  &.up {
    border-top: 3px solid #f56c6c;
    .index-value, .change-value {
      color: #f56c6c;
    }
  }

  &.down {
    border-top: 3px solid #67c23a;
    .index-value, .change-value {
      color: #67c23a;
    }
  }

  .index-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    .index-name {
      font-size: 16px;
      font-weight: bold;
      color: #303133;
    }

    .index-date {
      font-size: 14px;
      color: #909399;
    }
  }

  .index-main {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 15px;

    .index-value {
      font-size: 28px;
      font-weight: bold;
    }

    .index-change {
      text-align: right;

      .change-value {
        display: block;
        font-size: 18px;
        font-weight: bold;
      }
    }
  }

  .index-metrics {
    padding: 10px;
    background-color: #f5f7fa;
    border-radius: 4px;
    margin-bottom: 15px;

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
    }

    .metric-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      font-size: 13px;

      .label {
        color: #909399;
        margin-bottom: 4px;
      }

      .value {
        color: #606266;
        font-weight: 500;
      }
    }
  }
}

.chart-container {
  height: 400px;
  margin-top: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.min-chart-container {
  height: 400px;
  margin-top: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
</style> 