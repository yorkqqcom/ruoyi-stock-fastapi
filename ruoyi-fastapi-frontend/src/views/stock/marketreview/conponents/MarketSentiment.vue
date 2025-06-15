<template>
  <el-card class="box-card" v-loading="loading">
    <div slot="header" class="clearfix">
      <span>市场情绪</span>
    </div>
    <el-row :gutter="20">
      <el-col :span="6">
        <div class="sentiment-item">
          <div class="sentiment-title">市场概况</div>
          <div class="sentiment-content">
            <div class="market-overview">
              <div class="overview-section">
                <div class="section-title">涨跌停板</div>
                <div class="overview-grid">
                  <div class="overview-item">
                    <div class="item-label">涨停</div>
                    <div class="item-value up">{{ marketSentiment.upLimit }}</div>
                  </div>
                  <div class="overview-item">
                    <div class="item-label">跌停</div>
                    <div class="item-value down">{{ marketSentiment.downLimit }}</div>
                  </div>
                  <div class="overview-item">
                    <div class="item-label">涨跌比</div>
                    <div class="item-value">{{ marketSentiment.upLimit / (marketSentiment.upLimit + marketSentiment.downLimit) * 100 | toFixed(2) }}%</div>
                  </div>
                </div>
              </div>
              <div class="overview-section">
                <div class="section-title">涨跌家数</div>
                <div class="overview-grid">
                  <div class="overview-item">
                    <div class="item-label">上涨</div>
                    <div class="item-value up">{{ marketSentiment.upCount }}</div>
                  </div>
                  <div class="overview-item">
                    <div class="item-label">下跌</div>
                    <div class="item-value down">{{ marketSentiment.downCount }}</div>
                  </div>
                  <div class="overview-item">
                    <div class="item-label">市场宽度</div>
                    <div class="item-value" :class="{'up': marketSentiment.upCount > marketSentiment.downCount, 'down': marketSentiment.upCount < marketSentiment.downCount}">
                      {{ ((marketSentiment.upCount - marketSentiment.downCount) / (marketSentiment.upCount + marketSentiment.downCount) * 100) | toFixed(2) }}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="9">
        <div class="sentiment-item">
          <div class="sentiment-title">上涨概念板块</div>
          <div class="sentiment-content concept-list">
            <div v-for="(item, index) in conceptBoard.top_gainers.slice(0, 5)" :key="index" class="concept-item">
              <div class="concept-header">
                <div class="concept-info">
                  <span class="label">{{ item['板块名称'] }}</span>
                  <span class="leader-stock">领涨：{{ item['领涨股票'] }}(+{{ item['领涨股票-涨跌幅'].toFixed(2) }}%)</span>
                </div>
                <span class="value up">+{{ item['涨跌幅'].toFixed(2) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="9">
        <div class="sentiment-item">
          <div class="sentiment-title">下跌概念板块</div>
          <div class="sentiment-content concept-list">
            <div v-for="(item, index) in conceptBoard.top_losers.slice(0, 5)" :key="index" class="concept-item">
              <div class="concept-header">
                <div class="concept-info">
                  <span class="label">{{ item['板块名称'] }}</span>
                  <span class="leader-stock">领跌：{{ item['领涨股票'] }}({{ item['领涨股票-涨跌幅'].toFixed(2) }}%)</span>
                </div>
                <span class="value down">{{ item['涨跌幅'].toFixed(2) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script>
import { getMarketSentiment, getConceptBoardData } from '@/api/stock/market'

export default {
  name: 'MarketSentiment',
  data() {
    return {
      loading: false,
      marketSentiment: {
        upLimit: 0,
        downLimit: 0,
        upCount: 0,
        downCount: 0
      },
      conceptBoard: {
        top_gainers: [],
        top_losers: []
      }
    }
  },
  created() {
    this.initData()
  },
  methods: {
    async initData() {
      try {
        this.loading = true
        // 获取市场情绪数据
        const sentimentRes = await getMarketSentiment()
        if (sentimentRes.code === 200) {
          this.marketSentiment = sentimentRes.data
        }

        // 获取概念板块数据
        const conceptRes = await getConceptBoardData()
        if (conceptRes.code === 200) {
          this.conceptBoard = conceptRes.data
        }
      } catch (error) {
        console.error('获取数据失败：', error)
        this.$message.error('获取数据失败')
      } finally {
        this.loading = false
      }
    }
  },
  filters: {
    toFixed(value, digits = 2) {
      if (value === undefined || value === null) return '--'
      return Number(value).toFixed(digits)
    }
  }
}
</script>

<style lang="scss" scoped>
.sentiment-item {
  background-color: #fff;
  border-radius: 4px;
  padding: 15px;
  height: 100%;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

  .sentiment-title {
    font-size: 16px;
    font-weight: bold;
    color: #303133;
    margin-bottom: 15px;
  }

  .sentiment-content {
    height: calc(100% - 31px);
    overflow-y: auto;
  }
}

.market-overview {
  .overview-section {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      font-size: 14px;
      color: #606266;
      margin-bottom: 10px;
    }

    .overview-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }

    .overview-item {
      text-align: center;

      .item-label {
        font-size: 13px;
        color: #909399;
        margin-bottom: 5px;
      }

      .item-value {
        font-size: 18px;
        font-weight: bold;

        &.up {
          color: #f56c6c;
        }

        &.down {
          color: #67c23a;
        }
      }
    }
  }
}

.concept-list {
  .concept-item {
    padding: 10px;
    border-bottom: 1px solid #ebeef5;

    &:last-child {
      border-bottom: none;
    }

    .concept-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .concept-info {
        .label {
          font-size: 14px;
          color: #303133;
          margin-right: 10px;
        }

        .leader-stock {
          font-size: 12px;
          color: #909399;
        }
      }

      .value {
        font-size: 14px;
        font-weight: bold;

        &.up {
          color: #f56c6c;
        }

        &.down {
          color: #67c23a;
        }
      }
    }
  }
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}
</style> 