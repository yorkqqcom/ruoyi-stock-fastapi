<template>
  <el-card class="box-card" v-loading="loading">
    <div slot="header" class="clearfix">
      <span>资金流向</span>
    </div>
    <el-row :gutter="20">
      <el-col :span="6">
        <div class="fund-flow-item">
          <div class="fund-flow-title">主力资金</div>
          <div class="fund-flow-content">
            <div class="fund-amount" :class="{'inflow': fundFlow.amount > 0, 'outflow': fundFlow.amount < 0}">
              {{ fundFlow.amount ? (fundFlow.amount > 0 ? '+' : '') + fundFlow.amount.toFixed(2) : '0.00' }}亿
              <span class="fund-date" v-if="fundFlow.latestDate">({{ fundFlow.latestDate }})</span>
            </div>
            <div class="fund-detail">
              <div class="detail-item">
                <span class="label">净流入</span>
                <span class="value" :class="{'inflow': fundFlow.netInflow > 0, 'outflow': fundFlow.netInflow < 0}">
                  {{ fundFlow.netInflow ? (fundFlow.netInflow > 0 ? '+' : '') + fundFlow.netInflow.toFixed(2) : '0.00' }}亿
                </span>
                <div class="item-average" v-if="fundFlow.netInflow_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.netInflow_avg.toFixed(2) }}亿</span>
                </div>
              </div>
              <div class="detail-item">
                <span class="label">净流出</span>
                <span class="value" :class="{'inflow': fundFlow.netOutflow > 0, 'outflow': fundFlow.netOutflow < 0}">
                  {{ fundFlow.netOutflow ? (fundFlow.netOutflow > 0 ? '+' : '') + fundFlow.netOutflow.toFixed(2) : '0.00' }}亿
                </span>
                <div class="item-average" v-if="fundFlow.netOutflow_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.netOutflow_avg.toFixed(2) }}亿</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="margin-account-item">
          <div class="margin-account-title">融资融券余额</div>
          <div class="margin-account-content">
            <div class="margin-account-grid">
              <div class="margin-account-grid-item">
                <div class="item-label">融资余额</div>
                <div class="item-value highlight">{{ (fundFlow.margin_account && fundFlow.margin_account.financing_balance ? fundFlow.margin_account.financing_balance.toFixed(2) : '0.00') }}亿</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.financing_balance_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.financing_balance_avg.toFixed(2) }}亿</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">融券余额</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.securities_balance ? fundFlow.margin_account.securities_balance.toFixed(2) : '0.00') }}亿</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.securities_balance_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.securities_balance_avg.toFixed(2) }}亿</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">融资买入额</div>
                <div class="item-value" :class="{'inflow': fundFlow.margin_account && fundFlow.margin_account.financing_buy > 0}">
                  {{ (fundFlow.margin_account && fundFlow.margin_account.financing_buy ? fundFlow.margin_account.financing_buy.toFixed(2) : '0.00') }}亿
                </div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.financing_buy_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.financing_buy_avg.toFixed(2) }}亿</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">融券卖出额</div>
                <div class="item-value" :class="{'outflow': fundFlow.margin_account && fundFlow.margin_account.securities_sell > 0}">
                  {{ (fundFlow.margin_account && fundFlow.margin_account.securities_sell ? fundFlow.margin_account.securities_sell.toFixed(2) : '0.00') }}亿
                </div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.securities_sell_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.securities_sell_avg.toFixed(2) }}亿</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="margin-account-item">
          <div class="margin-account-title">融资融券投资者信息</div>
          <div class="margin-account-content">
            <div class="margin-account-grid">
              <div class="margin-account-grid-item">
                <div class="item-label">证券公司数量</div>
                <div class="item-value highlight">{{ (fundFlow.margin_account && fundFlow.margin_account.broker_count) || '0' }}家</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.broker_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.broker_count_avg }}家</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">营业部数量</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.branch_count) || '0' }}家</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.branch_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.branch_count_avg }}家</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">个人投资者</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.individual_investor_count ? fundFlow.margin_account.individual_investor_count.toFixed(2) : '0.00') }}万名</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.individual_investor_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.individual_investor_count_avg.toFixed(2) }}万名</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">机构投资者</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.institution_investor_count) || '0' }}家</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.institution_investor_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.institution_investor_count_avg }}家</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="margin-account-item">
          <div class="margin-account-title">融资融券交易信息</div>
          <div class="margin-account-content">
            <div class="margin-account-grid">
              <div class="margin-account-grid-item">
                <div class="item-label">参与交易投资者</div>
                <div class="item-value highlight">{{ (fundFlow.margin_account && fundFlow.margin_account.trading_investor_count) || '0' }}名</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.trading_investor_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.trading_investor_count_avg }}名</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">有负债投资者</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.debt_investor_count) || '0' }}名</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.debt_investor_count_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.debt_investor_count_avg }}名</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">担保物总价值</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.collateral_value ? fundFlow.margin_account.collateral_value.toFixed(2) : '0.00') }}亿</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.collateral_value_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.collateral_value_avg.toFixed(2) }}亿</span>
                </div>
              </div>
              <div class="margin-account-grid-item">
                <div class="item-label">平均维持担保比例</div>
                <div class="item-value">{{ (fundFlow.margin_account && fundFlow.margin_account.maintenance_ratio ? fundFlow.margin_account.maintenance_ratio.toFixed(2) : '0.00') }}%</div>
                <div class="item-average" v-if="fundFlow.margin_account && fundFlow.margin_account.maintenance_ratio_avg">
                  <span class="label">30日平均：</span>
                  <span class="value">{{ fundFlow.margin_account.maintenance_ratio_avg.toFixed(2) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="chart-container" ref="fundFlowChart" v-loading="loadingChart"></div>
  </el-card>
</template>

<script>
import * as echarts from 'echarts'
import { getFundFlow } from '@/api/stock/market'

export default {
  name: 'FundFlow',
  data() {
    return {
      loading: false,
      loadingChart: false,
      fundFlow: {
        amount: 0,
        netInflow: 0,
        netOutflow: 0,
        netInflow_avg: 0,
        netOutflow_avg: 0,
        latestDate: '',
        dates: [],
        mainMoneyData: [],
        margin_account: {
          financing_balance: 0,
          securities_balance: 0,
          financing_buy: 0,
          securities_sell: 0,
          trading_investor_count: 0,
          debt_investor_count: 0,
          collateral_value: 0,
          maintenance_ratio: 0,
          financing_balance_avg: 0,
          securities_balance_avg: 0,
          financing_buy_avg: 0,
          securities_sell_avg: 0,
          trading_investor_count_avg: 0,
          debt_investor_count_avg: 0,
          collateral_value_avg: 0,
          maintenance_ratio_avg: 0
        }
      }
    }
  },
  mounted() {
    this.initData()
    // 使用 nextTick 确保 DOM 已经渲染完成
    this.$nextTick(() => {
      this.initChart()
    })
    // 添加窗口大小变化监听
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    // 移除窗口大小变化监听
    window.removeEventListener('resize', this.handleResize)
    // 销毁图表实例
    if (this.fundFlowChart) {
      this.fundFlowChart.dispose()
    }
  },
  methods: {
    // 处理窗口大小变化
    handleResize() {
      if (this.fundFlowChart) {
        this.fundFlowChart.resize()
      }
    },
    async initData() {
      try {
        this.loading = true
        const fundFlowRes = await getFundFlow()
        if (fundFlowRes.code === 200) {
          this.fundFlow = fundFlowRes.data
          // 使用 nextTick 确保数据更新后再更新图表
          this.$nextTick(() => {
            this.updateFundFlowChart()
          })
        }
      } catch (error) {
        console.error('获取资金流向数据失败：', error)
        this.$message.error('获取资金流向数据失败')
      } finally {
        this.loading = false
      }
    },
    initChart() {
      if (this.$refs.fundFlowChart) {
        this.fundFlowChart = echarts.init(this.$refs.fundFlowChart)
        this.updateFundFlowChart()
      }
    },
    updateFundFlowChart() {
      if (!this.fundFlowChart || !this.fundFlow.dates || !this.fundFlow.mainMoneyData) {
        return
      }

      const option = {
        title: {
          text: '资金流向',
          left: 'center',
          top: 10
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: function(params) {
            const date = params[0].axisValue;
            const value = params[0].value;
            return `${date}<br/>${params[0].seriesName}：${value > 0 ? '+' : ''}${value}亿`;
          }
        },
        legend: {
          data: ['主力资金'],
          top: 40
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: this.fundFlow.dates,
          axisLabel: {
            rotate: 45,
            formatter: function(value) {
              return value.substring(5); // 只显示月-日
            }
          },
          axisTick: {
            alignWithLabel: true
          }
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: {
            formatter: function(value) {
              return value > 0 ? '+' + value.toFixed(0) + '亿' : value.toFixed(0) + '亿';
            }
          },
          splitLine: {
            show: true,
            lineStyle: {
              type: 'dashed'
            }
          }
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
            name: '主力资金',
            type: 'line',
            data: this.fundFlow.mainMoneyData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2
            },
            itemStyle: {
              color: function(params) {
                return params.value >= 0 ? '#f56c6c' : '#67c23a';
              }
            },
            areaStyle: {
              color: function(params) {
                const value = params.value;
                return {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [{
                    offset: 0,
                    color: value >= 0 ? 'rgba(245, 108, 108, 0.3)' : 'rgba(103, 194, 58, 0.3)'
                  }, {
                    offset: 1,
                    color: value >= 0 ? 'rgba(245, 108, 108, 0.1)' : 'rgba(103, 194, 58, 0.1)'
                  }]
                };
              }
            }
          }
        ]
      }
      this.fundFlowChart.setOption(option)
    }
  }
}
</script>

<style lang="scss" scoped>
.fund-flow-item {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  height: 100%;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }

  .fund-flow-title {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 15px;
    text-align: center;
    position: relative;
    padding-bottom: 8px;
    color: #303133;
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 30px;
      height: 2px;
      background-color: #409eff;
    }
  }

  .fund-flow-content {
    .fund-amount {
      font-size: 28px;
      margin-bottom: 15px;
      text-align: center;
      font-weight: bold;
      padding: 10px;
      background-color: #fff;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

      &.inflow {
        color: #f56c6c;
      }

      &.outflow {
        color: #67c23a;
      }

      .fund-date {
        font-size: 14px;
        color: #909399;
        margin-left: 8px;
        font-weight: normal;
      }
    }

    .fund-detail {
      .detail-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background-color: #fff;
        border-radius: 4px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

        &:last-child {
          margin-bottom: 0;
        }

        .label {
          color: #909399;
          font-size: 14px;
        }

        .value {
          font-size: 16px;
          font-weight: 500;

          &.inflow {
            color: #f56c6c;
          }

          &.outflow {
            color: #67c23a;
          }
        }
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

.margin-account-item {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  height: 100%;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }
  
  .margin-account-title {
    font-size: 16px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 15px;
    text-align: center;
    position: relative;
    padding-bottom: 8px;
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 30px;
      height: 2px;
      background-color: #409eff;
    }
  }
  
  .margin-account-content {
    .margin-account-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      
      .margin-account-grid-item {
        text-align: center;
        padding: 10px;
        background-color: #fff;
        border-radius: 4px;
        transition: all 0.3s;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        
        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }
        
        .item-label {
          font-size: 13px;
          color: #909399;
          margin-bottom: 6px;
        }
        
        .item-value {
          font-size: 16px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 4px;

          &.highlight {
            font-size: 18px;
            font-weight: bold;
            color: #409eff;
          }

          &.inflow {
            color: #f56c6c;
          }

          &.outflow {
            color: #67c23a;
          }
        }

        .item-average {
          font-size: 12px;
          color: #909399;
          padding-top: 4px;
          border-top: 1px dashed #dcdfe6;
          margin-top: 4px;

          .label {
            color: #909399;
          }

          .value {
            color: #606266;
            font-weight: 500;
          }
        }
      }
    }
  }
}

.inflow {
  color: #f56c6c;
}

.outflow {
  color: #67c23a;
}
</style> 