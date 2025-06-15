<template>
  <div class="review-section">
    <h3>市场复盘</h3>
    <div class="review-content markdown-body">
      <h4>1. 指数表现</h4>
      <ul>
        <li v-for="(index, key) in indexData.cards" :key="key">
          <span class="highlight-text">【{{ index.name }}】</span>：{{ index.value }}，涨跌幅{{ index.change > 0 ? '+' : '' }}{{ index.change.toFixed(2) }}%
          <span v-if="index.ma5 && index.ma10">
            (MA5: {{ formatValue(index.ma5) }}, MA10: {{ formatValue(index.ma10) }}, MA20: {{ formatValue(index.ma20) }})
          </span>
          <div class="technical-analysis">
            <span v-if="index.value > index.ma5 && index.ma5 > index.ma10 && index.ma10 > index.ma20" class="up-trend">
              > 均线系统呈现多头排列，短期趋势向好
            </span>
            <span v-else-if="index.value < index.ma5 && index.ma5 < index.ma10 && index.ma10 < index.ma20" class="down-trend">
              > 均线系统呈现空头排列，短期趋势承压
            </span>
            <span v-else class="neutral-trend">
              > 均线系统交织，市场处于震荡整理阶段
            </span>
          </div>
        </li>
      </ul>

      <h4>2. 市场情绪</h4>
      <ul>
        <li>涨停家数：<span class="highlight-text">{{ marketSentiment.upLimit }}</span>家，跌停家数：<span class="highlight-text">{{ marketSentiment.downLimit }}</span>家
          <span v-if="marketSentiment.upLimit > marketSentiment.downLimit" class="up-trend">
            > 市场情绪偏暖，赚钱效应明显
          </span>
          <span v-else-if="marketSentiment.upLimit < marketSentiment.downLimit" class="down-trend">
            > 市场情绪偏冷，需警惕风险
          </span>
          <span v-else class="neutral-trend">
            > 市场情绪中性，多空力量均衡
          </span>
        </li>
        <li>上涨家数：<span class="highlight-text">{{ marketSentiment.upCount }}</span>家，下跌家数：<span class="highlight-text">{{ marketSentiment.downCount }}</span>家
          <span v-if="marketSentiment.upCount > marketSentiment.downCount" class="up-trend">
            > 市场整体呈现普涨格局
          </span>
          <span v-else-if="marketSentiment.upCount < marketSentiment.downCount" class="down-trend">
            > 市场整体呈现普跌格局
          </span>
          <span v-else class="neutral-trend">
            > 市场呈现分化格局
          </span>
        </li>
        <li>市场情绪指标：<span class="highlight-text">{{ (marketSentiment.upCount / (marketSentiment.upCount + marketSentiment.downCount) * 100).toFixed(2) }}%</span>
          <span v-if="marketSentiment.upCount / (marketSentiment.upCount + marketSentiment.downCount) > 0.6" class="up-trend">
            > 市场情绪较为乐观
          </span>
          <span v-else-if="marketSentiment.upCount / (marketSentiment.upCount + marketSentiment.downCount) < 0.4" class="down-trend">
            > 市场情绪较为悲观
          </span>
          <span v-else class="neutral-trend">
            > 市场情绪中性
          </span>
        </li>
      </ul>

      <h4>3. 资金流向</h4>
      <ul>
        <li>主力资金：<span class="highlight-text">{{ fundFlow.amount ? (fundFlow.amount > 0 ? '+' : '') + fundFlow.amount.toFixed(2) : '0.00' }}亿</span>
          <span v-if="fundFlow.amount > 0" class="up-trend">
            > 主力资金呈现净流入，市场资金面较为宽松
          </span>
          <span v-else-if="fundFlow.amount < 0" class="down-trend">
            > 主力资金呈现净流出，市场资金面偏紧
          </span>
          <span v-else class="neutral-trend">
            > 主力资金进出平衡
          </span>
        </li>
        <li>融资融券：
          <ul>
            <li>融资余额：<span class="highlight-text">{{ (fundFlow.margin_account && fundFlow.margin_account.financing_balance ? fundFlow.margin_account.financing_balance.toFixed(2) : '0.00') }}亿</span>
              <span v-if="fundFlow.margin_account && fundFlow.margin_account.financing_balance > fundFlow.margin_account.financing_balance_avg" class="up-trend">
                > 融资余额高于30日均值，市场风险偏好提升
              </span>
              <span v-else class="down-trend">
                > 融资余额低于30日均值，市场风险偏好降低
              </span>
            </li>
            <li>融券余额：<span class="highlight-text">{{ (fundFlow.margin_account && fundFlow.margin_account.securities_balance ? fundFlow.margin_account.securities_balance.toFixed(2) : '0.00') }}亿</span>
              <span v-if="fundFlow.margin_account && fundFlow.margin_account.securities_balance > fundFlow.margin_account.securities_balance_avg" class="down-trend">
                > 融券余额高于30日均值，市场看空情绪增加
              </span>
              <span v-else class="up-trend">
                > 融券余额低于30日均值，市场看空情绪减弱
              </span>
            </li>
          </ul>
        </li>
      </ul>

      <h4>4. 板块表现</h4>
      <ul>
        <li>领涨板块：
          <ul>
            <li v-for="(item, index) in conceptBoard.top_gainers.slice(0, 3)" :key="'up-'+index">
              <span class="highlight-text">【{{ item['板块名称'] }}】</span>：涨幅{{ item['涨跌幅'].toFixed(2) }}%，领涨股<span class="highlight-text">{{ item['领涨股票'] }}</span>(+{{ item['领涨股票-涨跌幅'].toFixed(2) }}%)
              <span v-if="item['涨跌幅'] > 5" class="up-trend">
                > 板块表现强势，赚钱效应明显
              </span>
              <span v-else class="neutral-trend">
                > 板块表现一般，需关注持续性
              </span>
            </li>
          </ul>
        </li>
        <li>领跌板块：
          <ul>
            <li v-for="(item, index) in conceptBoard.top_losers.slice(0, 3)" :key="'down-'+index">
              <span class="highlight-text">【{{ item['板块名称'] }}】</span>：跌幅{{ item['涨跌幅'].toFixed(2) }}%，领跌股<span class="highlight-text">{{ item['领涨股票'] }}</span>({{ item['领涨股票-涨跌幅'].toFixed(2) }}%)
              <span v-if="item['涨跌幅'] < -5" class="down-trend">
                > 板块表现弱势，需警惕风险
              </span>
              <span v-else class="neutral-trend">
                > 板块小幅调整，可关注超跌机会
              </span>
            </li>
          </ul>
        </li>
      </ul>

      <h4>5. 龙虎榜分析</h4>
      <ul>
        <li>机构资金动向：
          <ul>
            <li v-for="(item, index) in (lhbData && lhbData.institution_trading ? lhbData.institution_trading.slice(0, 3) : [])" :key="'inst-'+index">
              <span class="highlight-text">【{{ item['机构名称'] }}】</span>：净买入{{ (item['净买入额'] / 100000000).toFixed(2) }}亿
              <span v-if="item['净买入额'] > 0" class="up-trend">
                > 机构资金积极布局
              </span>
              <span v-else class="down-trend">
                > 机构资金谨慎观望
              </span>
            </li>
          </ul>
        </li>
        <li>活跃营业部：
          <ul>
            <li v-for="(item, index) in (lhbData && lhbData.broker_ranking ? lhbData.broker_ranking.slice(0, 3) : [])" :key="'broker-'+index">
              <span class="highlight-text">【{{ item['营业部名称'] }}】</span>：上榜{{ item['上榜次数'] }}次，年内3日跟买成功率{{ (item['年内3日跟买成功率'] * 100).toFixed(2) }}%
              <span v-if="item['年内3日跟买成功率'] > 0.6" class="up-trend">
                > 营业部操作成功率较高，可重点关注
              </span>
              <span v-else class="neutral-trend">
                > 营业部操作成功率一般，需谨慎参考
              </span>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MarketReview',
  props: {
    indexData: {
      type: Object,
      required: true
    },
    marketSentiment: {
      type: Object,
      required: true
    },
    fundFlow: {
      type: Object,
      required: true
    },
    conceptBoard: {
      type: Object,
      required: true
    },
    lhbData: {
      type: Object,
      required: true
    }
  },
  methods: {
    formatValue(value) {
      if (value === undefined || value === null) return '--';
      return Number(value).toFixed(2);
    }
  }
}
</script>

<style lang="scss" scoped>
.review-section {
  height: 100%;
  margin-bottom: 0;

  h3 {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 20px;
    color: #303133;
    border-bottom: 2px solid #409eff;
    padding-bottom: 10px;
  }

  h4 {
    font-size: 16px;
    font-weight: bold;
    margin: 15px 0;
    color: #409eff;
  }

  .review-content {
    height: calc(100% - 60px);
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background-color: #dcdfe6;
      border-radius: 2px;
    }
  }
}

.highlight-text {
  color: #f56c6c;
  font-weight: bold;
  font-size: 1.1em;
}

.up-trend {
  color: #f56c6c;
  font-weight: 500;
}

.down-trend {
  color: #67c23a;
  font-weight: 500;
}

.neutral-trend {
  color: #909399;
  font-weight: 500;
}

.technical-analysis {
  margin-top: 8px;
  padding-left: 20px;
  border-left: 2px solid #dcdfe6;
}

.markdown-body {
  :deep(h4) {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
    color: #409eff;
  }

  :deep(ul) {
    padding-left: 2em;
    margin-top: 0;
    margin-bottom: 16px;
  }

  :deep(li) {
    margin-top: 0.25em;
  }
}
</style> 