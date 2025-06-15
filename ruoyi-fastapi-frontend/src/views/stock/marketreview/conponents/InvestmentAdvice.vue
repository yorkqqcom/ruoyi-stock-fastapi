<template>
  <div class="suggestion-section">
    <h3>投资建议</h3>
    <div class="suggestion-content markdown-body">
      <h4>1. 技术面分析</h4>
      <ul>
        <li v-for="(index, key) in indexData.cards" :key="key">
          **{{ index.name }}**：
          <span v-if="index.value > index.ma5 && index.ma5 > index.ma10 && index.ma10 > index.ma20">
            > 短期趋势向上，均线系统呈现多头排列，可考虑逢低布局
          </span>
          <span v-else-if="index.value < index.ma5 && index.ma5 < index.ma10 && index.ma10 < index.ma20">
            > 短期趋势向下，均线系统呈现空头排列，建议观望为主
          </span>
          <span v-else>
            > 短期趋势震荡，建议高抛低吸，控制仓位
          </span>
        </li>
      </ul>

      <h4>2. 市场趋势判断</h4>
      <ul>
        <li v-if="marketSentiment.upCount > marketSentiment.downCount && fundFlow.amount > 0">
          > 市场整体呈现强势上涨趋势，投资者情绪较为乐观，资金面较为宽松
          <ul>
            <li>建议：可适当提高仓位，关注强势板块机会</li>
            <li>风险提示：注意防范追高风险，设置合理止损位</li>
          </ul>
        </li>
        <li v-else-if="marketSentiment.upCount > marketSentiment.downCount && fundFlow.amount < 0">
          > 市场呈现结构性上涨，但资金面偏紧，需警惕回调风险
          <ul>
            <li>建议：控制仓位，关注资金流入板块机会</li>
            <li>风险提示：注意防范资金面收紧带来的调整风险</li>
          </ul>
        </li>
        <li v-else-if="marketSentiment.upCount < marketSentiment.downCount && fundFlow.amount > 0">
          > 市场呈现结构性调整，但资金面较为宽松，可关注超跌反弹机会
          <ul>
            <li>建议：可逢低布局超跌优质个股</li>
            <li>风险提示：注意防范市场情绪低迷带来的持续调整风险</li>
          </ul>
        </li>
        <li v-else>
          > 市场整体呈现弱势，投资者情绪较为谨慎，资金面偏紧
          <ul>
            <li>建议：以防御为主，控制仓位，等待市场企稳</li>
            <li>风险提示：注意防范市场持续调整风险</li>
          </ul>
        </li>
      </ul>

      <h4>3. 资金面建议</h4>
      <ul>
        <li>主力资金：{{ fundFlow.amount ? (fundFlow.amount > 0 ? '+' : '') + fundFlow.amount.toFixed(2) : '0.00' }}亿
          <span v-if="fundFlow.amount > 0">
            > 建议：可适当提高仓位，关注强势板块机会
          </span>
          <span v-else-if="fundFlow.amount < 0">
            > 建议：控制仓位，以防御为主
          </span>
          <span v-else>
            > 建议：保持中性仓位，等待方向明确
          </span>
        </li>
        <li>融资融券：
          <ul>
            <li>融资余额：{{ (fundFlow.margin_account && fundFlow.margin_account.financing_balance ? fundFlow.margin_account.financing_balance.toFixed(2) : '0.00') }}亿
              <span v-if="fundFlow.margin_account && fundFlow.margin_account.financing_balance > fundFlow.margin_account.financing_balance_avg">
                > 建议：注意控制融资规模，防范杠杆风险
              </span>
              <span v-else>
                > 建议：可适当增加融资规模，把握市场机会
              </span>
            </li>
            <li>融券余额：{{ (fundFlow.margin_account && fundFlow.margin_account.securities_balance ? fundFlow.margin_account.securities_balance.toFixed(2) : '0.00') }}亿
              <span v-if="fundFlow.margin_account && fundFlow.margin_account.securities_balance > fundFlow.margin_account.securities_balance_avg">
                > 建议：可适当增加融券操作，把握做空机会
              </span>
              <span v-else>
                > 建议：谨慎做空，关注市场企稳信号
              </span>
            </li>
          </ul>
        </li>
      </ul>

      <h4>4. 板块机会分析</h4>
      <ul>
        <li>强势板块：
          <ul>
            <li v-for="(item, index) in conceptBoard.top_gainers.slice(0, 3)" :key="'up-'+index">
              > **{{ item['板块名称'] }}**板块表现强势，领涨股{{ item['领涨股票'] }}涨幅达{{ item['领涨股票-涨跌幅'].toFixed(2) }}%
              <ul>
                <li>建议：可关注板块内其他优质个股机会</li>
                <li>风险提示：注意防范追高风险，关注板块持续性</li>
              </ul>
            </li>
          </ul>
        </li>
        <li>超跌板块：
          <ul>
            <li v-for="(item, index) in conceptBoard.top_losers.slice(0, 3)" :key="'down-'+index">
              > **{{ item['板块名称'] }}**板块出现超跌，领跌股{{ item['领涨股票'] }}跌幅达{{ item['领涨股票-涨跌幅'].toFixed(2) }}%
              <ul>
                <li>建议：可关注超跌反弹机会，分批布局</li>
                <li>风险提示：注意防范持续调整风险，关注基本面变化</li>
              </ul>
            </li>
          </ul>
        </li>
      </ul>

      <h4>5. 机构资金分析</h4>
      <ul>
        <li>机构动向：
          <ul>
            <li v-for="(item, index) in lhbData.institution_trading.slice(0, 3)" :key="'inst-'+index">
              > **{{ item['机构名称'] }}**近期净买入{{ (item['净买入额'] / 100000000).toFixed(2) }}亿
              <ul>
                <li>建议：可关注机构资金布局方向</li>
                <li>风险提示：注意防范机构资金撤离风险</li>
              </ul>
            </li>
          </ul>
        </li>
        <li>营业部特征：
          <ul>
            <li v-for="(item, index) in lhbData.broker_ranking.slice(0, 3)" :key="'broker-'+index">
              > **{{ item['营业部名称'] }}**上榜{{ item['上榜次数'] }}次，年内3日跟买成功率{{ (item['年内3日跟买成功率'] * 100).toFixed(2) }}%
              <ul>
                <li>建议：可参考营业部操作方向</li>
                <li>风险提示：注意防范跟风风险，关注个股基本面</li>
              </ul>
            </li>
          </ul>
        </li>
      </ul>

      <h4>6. 风险提示</h4>
      <div class="risk-warning">
        <ul>
          <li>市场波动风险：关注指数技术面变化，及时调整策略</li>
          <li>板块轮动风险：注意板块轮动节奏，避免追高</li>
          <li>资金面风险：关注主力资金流向变化，警惕资金面收紧</li>
          <li>机构资金风险：关注机构资金动向变化，警惕机构资金撤离</li>
          <li>概念板块风险：警惕概念板块炒作风险，注意基本面支撑</li>
          <li>融资融券风险：关注融资融券余额变化，警惕杠杆风险</li>
          <li>营业部跟风风险：注意防范跟风风险，关注个股基本面</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InvestmentAdvice',
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
  }
}
</script>

<style lang="scss" scoped>
.suggestion-section {
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

  .suggestion-content {
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

.risk-warning {
  background-color: #fef0f0;
  padding: 15px;
  border-radius: 4px;
  border-left: 4px solid #f56c6c;
  margin: 15px 0;

  ul {
    margin: 0;
    padding-left: 20px;

    li {
      color: #f56c6c;
      margin-bottom: 8px;
      line-height: 1.6;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
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

  :deep(strong) {
    font-weight: 600;
  }
}
</style> 