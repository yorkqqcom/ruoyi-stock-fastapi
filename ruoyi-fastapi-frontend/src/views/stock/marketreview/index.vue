<template>
  <div class="app-container">

    <el-row :gutter="20">
      <!-- 指数分析卡片 -->
      <el-col :span="24">
        <index-analysis />
      </el-col>

      <!-- 市场情绪卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <market-sentiment />
      </el-col>

      <!-- 市场复盘和建议卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <el-card class="box-card" v-loading="loading.reviewData">
          <div slot="header" class="clearfix">
            <span>市场复盘与投资建议</span>
          </div>
          <div class="review-container">
            <el-row :gutter="20">
              <el-col :span="12">
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
              </el-col>
              <el-col :span="12">
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
                          <li>融资买入额：{{ (fundFlow.margin_account && fundFlow.margin_account.financing_buy ? fundFlow.margin_account.financing_buy.toFixed(2) : '0.00') }}亿
                            <span v-if="fundFlow.margin_account && fundFlow.margin_account.financing_buy > fundFlow.margin_account.financing_buy_avg">
                              > 建议：可跟随融资资金布局，关注融资买入较多的板块
                            </span>
                            <span v-else>
                              > 建议：谨慎融资买入，等待市场企稳
                            </span>
                          </li>
                          <li>融券卖出额：{{ (fundFlow.margin_account && fundFlow.margin_account.securities_sell ? fundFlow.margin_account.securities_sell.toFixed(2) : '0.00') }}亿
                            <span v-if="fundFlow.margin_account && fundFlow.margin_account.securities_sell > fundFlow.margin_account.securities_sell_avg">
                              > 建议：可关注融券卖出较多的板块，把握做空机会
                            </span>
                            <span v-else>
                              > 建议：谨慎做空，关注市场企稳信号
                            </span>
                          </li>
                          <li>参与交易投资者：{{ (fundFlow.margin_account && fundFlow.margin_account.trading_investor_count) || '0' }}名
                            <span v-if="fundFlow.margin_account && fundFlow.margin_account.trading_investor_count > fundFlow.margin_account.trading_investor_count_avg">
                              > 建议：可适当提高交易频率，把握市场机会
                            </span>
                            <span v-else>
                              > 建议：降低交易频率，等待市场活跃度提升
                            </span>
                          </li>
                          <li>有负债投资者：{{ (fundFlow.margin_account && fundFlow.margin_account.debt_investor_count) || '0' }}名
                            <span v-if="fundFlow.margin_account && fundFlow.margin_account.debt_investor_count > fundFlow.margin_account.debt_investor_count_avg">
                              > 建议：注意控制杠杆比例，防范系统性风险
                            </span>
                            <span v-else>
                              > 建议：可适当提高杠杆比例，把握市场机会
                            </span>
                          </li>
                          <li>平均维持担保比例：{{ (fundFlow.margin_account && fundFlow.margin_account.maintenance_ratio ? fundFlow.margin_account.maintenance_ratio.toFixed(2) : '0.00') }}%
                            <span v-if="fundFlow.margin_account && fundFlow.margin_account.maintenance_ratio > 300">
                              > 建议：可适当提高融资比例，把握市场机会
                            </span>
                            <span v-else-if="fundFlow.margin_account && fundFlow.margin_account.maintenance_ratio > 200">
                              > 建议：降低融资比例，防范风险
                            </span>
                            <span v-else>
                              > 建议：及时降低杠杆，防范强平风险
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
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>

      <!-- 资金流向卡片 -->
      <el-col :span="24">
        <fund-flow />
      </el-col>

      <!-- 板块分析卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <el-card class="box-card" v-loading="loading.conceptBoard">
          <div slot="header" class="clearfix">
            <span>板块分析</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="board-section">
                <h3>领涨板块</h3>
                <el-table :data="conceptBoard.top_gainers" style="width: 100%" size="small">
                  <el-table-column prop="板块名称" label="板块名称" width="120"></el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row.涨跌幅 > 0, 'down': scope.row.涨跌幅 < 0}">
                        {{ scope.row.涨跌幅 > 0 ? '+' : '' }}{{ scope.row.涨跌幅.toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="领涨股票" label="领涨股票" width="120"></el-table-column>
                  <el-table-column prop="领涨股票-涨跌幅" label="领涨股涨幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row['领涨股票-涨跌幅'] > 0, 'down': scope.row['领涨股票-涨跌幅'] < 0}">
                        {{ scope.row['领涨股票-涨跌幅'] > 0 ? '+' : '' }}{{ scope.row['领涨股票-涨跌幅'].toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="board-section">
                <h3>领跌板块</h3>
                <el-table :data="conceptBoard.top_losers" style="width: 100%" size="small">
                  <el-table-column prop="板块名称" label="板块名称" width="120"></el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row.涨跌幅 > 0, 'down': scope.row.涨跌幅 < 0}">
                        {{ scope.row.涨跌幅 > 0 ? '+' : '' }}{{ scope.row.涨跌幅.toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="领涨股票" label="领跌股票" width="120"></el-table-column>
                  <el-table-column prop="领涨股票-涨跌幅" label="领跌股跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row['领涨股票-涨跌幅'] > 0, 'down': scope.row['领涨股票-涨跌幅'] < 0}">
                        {{ scope.row['领涨股票-涨跌幅'] > 0 ? '+' : '' }}{{ scope.row['领涨股票-涨跌幅'].toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 板块资金流向卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <el-card class="box-card" v-loading="loading.sectorFundFlow">
          <div slot="header" class="clearfix">
            <span>板块资金流向</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="fund-flow-section">
                <h3>行业资金流向</h3>
                <el-table :data="(sectorFundFlow && sectorFundFlow.industry_flow ? sectorFundFlow.industry_flow.slice(0, 10) : [])" style="width: 100%" size="small">
                  <el-table-column prop="名称" label="行业名称" min-width="120">
                    <template slot-scope="scope">
                      <div class="sector-name">
                        <span class="name">{{ scope.row.名称 || '--' }}</span>
                        <el-tag size="mini" type="info" effect="plain">行业</el-tag>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row.涨跌幅 > 0, 'down': scope.row.涨跌幅 < 0}">
                        {{ scope.row.涨跌幅 > 0 ? '+' : '' }}{{ scope.row.涨跌幅.toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="主力净流入-净额" label="主力净流入" width="120">
                    <template slot-scope="scope">
                      <div class="fund-flow-value">
                        <span :class="{'inflow': scope.row['主力净流入-净额'] > 0, 'outflow': scope.row['主力净流入-净额'] < 0}">
                          {{ scope.row['主力净流入-净额'] > 0 ? '+' : '' }}{{ (scope.row['主力净流入-净额'] / 100000000).toFixed(2) }}亿
                        </span>
                        <el-progress 
                          :percentage="Math.abs(scope.row['主力净流入-净占比'])" 
                          :color="scope.row['主力净流入-净额'] > 0 ? '#f56c6c' : '#67c23a'"
                          :show-text="false"
                          :stroke-width="4">
                        </el-progress>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="主力净流入最大股" label="领涨股" min-width="120">
                    <template slot-scope="scope">
                      <div class="max-stock">
                        <span class="stock-name">{{ scope.row['主力净流入最大股'] || '--' }}</span>
                        <span class="stock-change" :class="{'up': scope.row['主力净流入最大股-涨跌幅'] > 0, 'down': scope.row['主力净流入最大股-涨跌幅'] < 0}">
                          {{ scope.row['主力净流入最大股-涨跌幅'] > 0 ? '+' : '' }}{{ scope.row['主力净流入最大股-涨跌幅'] !== undefined ? scope.row['主力净流入最大股-涨跌幅'].toFixed(2) : '--' }}%
                        </span>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="fund-flow-section">
                <h3>概念资金流向</h3>
                <el-table :data="(sectorFundFlow && sectorFundFlow.concept_flow ? sectorFundFlow.concept_flow.slice(0, 10) : [])" style="width: 100%" size="small">
                  <el-table-column prop="名称" label="概念名称" min-width="120">
                    <template slot-scope="scope">
                      <div class="sector-name">
                        <span class="name">{{ scope.row.名称 || '--' }}</span>
                        <el-tag size="mini" type="info" effect="plain">概念</el-tag>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row.涨跌幅 > 0, 'down': scope.row.涨跌幅 < 0}">
                        {{ scope.row.涨跌幅 > 0 ? '+' : '' }}{{ scope.row.涨跌幅.toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="主力净流入-净额" label="主力净流入" width="120">
                    <template slot-scope="scope">
                      <div class="fund-flow-value">
                        <span :class="{'inflow': scope.row['主力净流入-净额'] > 0, 'outflow': scope.row['主力净流入-净额'] < 0}">
                          {{ scope.row['主力净流入-净额'] > 0 ? '+' : '' }}{{ (scope.row['主力净流入-净额'] / 100000000).toFixed(2) }}亿
                        </span>
                        <el-progress 
                          :percentage="Math.abs(scope.row['主力净流入-净占比'])" 
                          :color="scope.row['主力净流入-净额'] > 0 ? '#f56c6c' : '#67c23a'"
                          :show-text="false"
                          :stroke-width="4">
                        </el-progress>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="主力净流入最大股" label="领涨股" min-width="120">
                    <template slot-scope="scope">
                      <div class="max-stock">
                        <span class="stock-name">{{ scope.row['主力净流入最大股'] || '--' }}</span>
                        <span class="stock-change" :class="{'up': scope.row['主力净流入最大股-涨跌幅'] > 0, 'down': scope.row['主力净流入最大股-涨跌幅'] < 0}">
                          {{ scope.row['主力净流入最大股-涨跌幅'] > 0 ? '+' : '' }}{{ scope.row['主力净流入最大股-涨跌幅'] !== undefined ? scope.row['主力净流入最大股-涨跌幅'].toFixed(2) : '--' }}%
                        </span>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 涨停跌停股票卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <el-card class="box-card" v-loading="loading.limitStocks">
          <div slot="header" class="clearfix">
            <span>涨停跌停股票</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="limit-stocks-section">
                <h3>
                  <i class="el-icon-top-right up-icon"></i>
                  涨停股票
                  <span class="stock-count">({{ limitStocks.limit_up_stocks.length }})</span>
                </h3>
                <el-table 
                  :data="limitStocks.limit_up_stocks" 
                  style="width: 100%" 
                  size="small"
                  v-loading="loading.limitStocks">
                  <template slot="empty">
                    <div class="empty-data">
                      <i class="el-icon-warning"></i>
                      <span>暂无数据</span>
                    </div>
                  </template>
                  <el-table-column prop="代码" label="代码" width="100">
                    <template slot-scope="scope">
                      <span class="stock-code">{{ scope.row.代码 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="名称" label="名称" width="100">
                    <template slot-scope="scope">
                      <span class="stock-name">{{ scope.row.名称 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span class="up">+{{ scope.row.涨跌幅.toFixed(2) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="连板数" label="连板数" width="80">
                    <template slot-scope="scope">
                      <el-tag 
                        size="mini" 
                        type="danger" 
                        effect="dark"
                        v-if="scope.row.连板数 > 1">
                        {{ scope.row.连板数 }}连板
                      </el-tag>
                      <span v-else>--</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="所属行业" label="所属行业" min-width="120">
                    <template slot-scope="scope">
                      <el-tag 
                        size="mini" 
                        type="info" 
                        effect="plain">
                        {{ scope.row.所属行业 || '--' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="最新价" label="最新价" width="100">
                    <template slot-scope="scope">
                      <span class="price">{{ scope.row.最新价 ? scope.row.最新价.toFixed(2) : '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="换手率" label="换手率" width="100">
                    <template slot-scope="scope">
                      <span>{{ scope.row.换手率 ? scope.row.换手率.toFixed(2) + '%' : '--' }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="limit-stocks-section">
                <h3>
                  <i class="el-icon-bottom-right down-icon"></i>
                  跌停股票
                  <span class="stock-count">({{ limitStocks.limit_down_stocks.length }})</span>
                </h3>
                <el-table 
                  :data="limitStocks.limit_down_stocks" 
                  style="width: 100%" 
                  size="small"
                  v-loading="loading.limitStocks">
                  <template slot="empty">
                    <div class="empty-data">
                      <i class="el-icon-warning"></i>
                      <span>暂无数据</span>
                    </div>
                  </template>
                  <el-table-column prop="代码" label="代码" width="100">
                    <template slot-scope="scope">
                      <span class="stock-code">{{ scope.row.代码 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="名称" label="名称" width="100">
                    <template slot-scope="scope">
                      <span class="stock-name">{{ scope.row.名称 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span class="down">{{ scope.row.涨跌幅.toFixed(2) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="连续跌停" label="连续跌停" width="80">
                    <template slot-scope="scope">
                      <el-tag 
                        size="mini" 
                        type="success" 
                        effect="dark"
                        v-if="scope.row.连续跌停 > 1">
                        {{ scope.row.连续跌停 }}连跌
                      </el-tag>
                      <span v-else>--</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="所属行业" label="所属行业" min-width="120">
                    <template slot-scope="scope">
                      <el-tag 
                        size="mini" 
                        type="info" 
                        effect="plain">
                        {{ scope.row.所属行业 || '--' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="最新价" label="最新价" width="100">
                    <template slot-scope="scope">
                      <span class="price">{{ scope.row.最新价 ? scope.row.最新价.toFixed(2) : '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="换手率" label="换手率" width="100">
                    <template slot-scope="scope">
                      <span>{{ scope.row.换手率 ? scope.row.换手率.toFixed(2) + '%' : '--' }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 龙虎榜卡片 -->
      <el-col :span="24" style="margin-top: 20px;">
        <el-card class="box-card" v-loading="loading.lhbData">
          <div slot="header" class="clearfix">
            <span>龙虎榜数据</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="24">
              <div class="lhb-section">
                <h3>龙虎榜详情</h3>
                <el-table 
                  :data="lhbData && lhbData.lhb_details ? lhbData.lhb_details : []" 
                  style="width: 100%" 
                  size="small"
                  v-loading="loading.lhbData">
                  <template slot="empty">
                    <div class="empty-data">
                      <i class="el-icon-warning"></i>
                      <span>暂无数据</span>
                    </div>
                  </template>
                  <el-table-column prop="代码" label="代码" width="100">
                    <template slot-scope="scope">
                      <span class="stock-code">{{ scope.row.代码 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="名称" label="名称" width="100">
                    <template slot-scope="scope">
                      <span class="stock-name">{{ scope.row.名称 || '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
                    <template slot-scope="scope">
                      <span :class="{'up': scope.row.涨跌幅 > 0, 'down': scope.row.涨跌幅 < 0}">
                        {{ scope.row.涨跌幅 > 0 ? '+' : '' }}{{ scope.row.涨跌幅.toFixed(2) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="龙虎榜净买额" label="净买额" width="120">
                    <template slot-scope="scope">
                      <span :class="{'inflow': scope.row.龙虎榜净买额 > 0, 'outflow': scope.row.龙虎榜净买额 < 0}">
                        {{ scope.row.龙虎榜净买额 > 0 ? '+' : '' }}{{ (scope.row.龙虎榜净买额 / 100000000).toFixed(2) }}亿
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="上榜原因" label="上榜原因" min-width="200">
                    <template slot-scope="scope">
                      <el-tooltip 
                        :content="scope.row.上榜原因" 
                        placement="top" 
                        :disabled="!scope.row.上榜原因">
                        <span class="reason-text">{{ scope.row.上榜原因 || '--' }}</span>
                      </el-tooltip>
                    </template>
                  </el-table-column>
                  <el-table-column prop="收盘价" label="收盘价" width="100">
                    <template slot-scope="scope">
                      <span>{{ scope.row.收盘价 ? scope.row.收盘价.toFixed(2) : '--' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="换手率" label="换手率" width="100">
                    <template slot-scope="scope">
                      <span>{{ scope.row.换手率 ? scope.row.换手率.toFixed(2) + '%' : '--' }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
          </el-row>

          <!-- 添加营业部排行表格 -->
          <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :span="24">
              <div class="lhb-section">
                <h3>营业部排行</h3>
                <el-table 
                  :data="lhbData.broker_ranking" 
                  style="width: 100%" 
                  size="small"
                  v-loading="loading.lhbData">
                  <template slot="empty">
                    <div class="empty-data">
                      <i class="el-icon-warning"></i>
                      <span>暂无数据</span>
                    </div>
                  </template>
                  <el-table-column prop="序号" label="序号" width="80"></el-table-column>
                  <el-table-column prop="营业部名称" label="营业部名称" min-width="500">
                    <template slot-scope="scope">
                      <div class="broker-name">
                        <div class="name-wrapper">
                          <span class="name">{{ scope.row.营业部名称 }}</span>
                          <el-tag 
                            v-if="scope.row.标签" 
                            size="mini" 
                            type="warning" 
                            effect="plain">
                            {{ scope.row.标签 }}
                          </el-tag>
                        </div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="上榜次数" label="上榜次数" width="100"></el-table-column>
                  <el-table-column prop="合计动用资金" label="合计动用资金" width="120">
                    <template slot-scope="scope">
                      <span>{{ formatBrokerAmount(scope.row.合计动用资金) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="年内上榜次数" label="年内上榜次数" width="120"></el-table-column>
                  <el-table-column prop="年内买入股票只数" label="年内买入股票只数" width="150"></el-table-column>
                  <el-table-column prop="年内3日跟买成功率" label="年内3日跟买成功率" width="150">
                    <template slot-scope="scope">
                      <span>{{ (scope.row.年内3日跟买成功率 * 100).toFixed(2) }}%</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { 
  getIndexData, 
  getMarketSentiment, 
  getFundFlow, 
  getMainIndicesMinData,
  getConceptBoardData,
  getSectorFundFlow,
  getLimitStocks,
  getLhbData,
  getMarketAnalysis
} from '@/api/stock/market'
import IndexAnalysis from './conponents/IndexAnalysis.vue'
import MarketSentiment from './conponents/MarketSentiment.vue'
import FundFlow from './conponents/FundFlow'

export default {
  name: 'MarketReview',
  components: {
    IndexAnalysis,
    MarketSentiment,
    FundFlow
  },
  data() {
    return {
      loading: {
        marketSentiment: false,
        reviewData: false,
        fundFlow: false,
        fundFlowChart: false,
        lhbData: false,
        sectorFundFlow: false,
        limitStocks: false
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
      limitStocks: {
        limit_up_stocks: [],
        limit_down_stocks: []
      },
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
      },
      sectorFundFlow: {
        industry_flow: [],
        concept_flow: []
      },
      lhbData: {
        lhb_details: [],
        institution_trading: [],
        broker_ranking: []
      },
      marketSentiment: {
        upLimit: 0,
        downLimit: 0,
        upCount: 0,
        downCount: 0
      },
      conceptBoard: {
        top_gainers: [],
        top_losers: []
      },
      reviewData: {
        market_review: '',
        investment_advice: ''
      }
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
    if (this.fundFlowChart) {
      this.fundFlowChart.dispose()
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
      if (this.fundFlowChart) {
        this.fundFlowChart.resize()
      }
    },
    // 格式化板块资金流向数据
    formatSectorFundFlow(data) {
      if (!data || !Array.isArray(data)) {
        return []
      }
      const formatted = data.map(item => ({
        ...item,
        '主力净流入-净额': Number(item['主力净流入-净额']) || 0,
        '主力净流入-净占比': Number(item['主力净流入-净占比']) || 0,
        '今日涨跌幅': Number(item['今日涨跌幅']) || 0,
        '主力净流入最大股-涨跌幅': Number(item['主力净流入最大股-涨跌幅']) || 0
      }))
      return formatted
    },
    async initData() {
      try {
        // 获取指数数据
        const indexRes = await getIndexData()
        if (indexRes.code === 200) {
          this.indexData = indexRes.data
        }

        // 获取市场情绪数据
        this.loading.marketSentiment = true
        const sentimentRes = await getMarketSentiment()
        if (sentimentRes.code === 200) {
          this.marketSentiment = sentimentRes.data
        }
        this.loading.marketSentiment = false

        // 获取概念板块数据
        this.loading.conceptBoard = true
        const conceptRes = await getConceptBoardData()
        if (conceptRes.code === 200) {
          this.conceptBoard = conceptRes.data
        }
        this.loading.conceptBoard = false

        // 获取市场分析数据
        this.loading.reviewData = true
        const reviewRes = await getMarketAnalysis()
        if (reviewRes.code === 200) {
          this.reviewData = reviewRes.data
        }
        this.loading.reviewData = false

        // 获取资金流向数据
        this.loading.fundFlow = true
        const fundFlowRes = await getFundFlow()
        if (fundFlowRes.code === 200) {
          this.fundFlow = fundFlowRes.data
          // 使用 nextTick 确保数据更新后再更新图表
          this.$nextTick(() => {
            this.updateFundFlowChart()
          })
        }
        this.loading.fundFlow = false

        // 获取龙虎榜数据
        this.loading.lhbData = true
        const lhbRes = await getLhbData()
        if (lhbRes.code === 200) {
          this.lhbData = lhbRes.data
        }
        this.loading.lhbData = false

        // 获取板块资金流向数据
        this.loading.sectorFundFlow = true
        const sectorFundFlowRes = await getSectorFundFlow()
        if (sectorFundFlowRes.code === 200) {
          this.sectorFundFlow = sectorFundFlowRes.data
        }
        this.loading.sectorFundFlow = false

        // 获取涨停跌停股票数据
        this.loading.limitStocks = true
        const limitStocksRes = await getLimitStocks()
        if (limitStocksRes.code === 200) {
          this.limitStocks = limitStocksRes.data
        }
        this.loading.limitStocks = false
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

      if (this.$refs.fundFlowChart) {
        this.fundFlowChart = echarts.init(this.$refs.fundFlowChart)
        this.updateFundFlowChart()
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
    },

    // 格式化资金流向金额
    formatFundAmount(amount) {
      if (amount === undefined || amount === null) return '0.00';
      const value = Number(amount);
      return (value / 100000000).toFixed(2);
    },
    // 格式化营业部金额
    formatBrokerAmount(amount) {
      if (!amount) return '--';
      // 如果已经是格式化后的字符串，直接返回
      if (typeof amount === 'string' && (amount.includes('亿') || amount.includes('万'))) {
        return amount;
      }
      // 如果是数字，进行格式化
      const value = Number(amount);
      if (value >= 100000000) {
        return (value / 100000000).toFixed(2) + '亿';
      } else if (value >= 10000) {
        return (value / 10000).toFixed(2) + '万';
      }
      return value.toFixed(2);
    },
    // 处理分时行情数据
    processMinData(data) {
      if (!data || !data.sh || !data.sz || !data.cyb) {
        console.error('分时行情数据不完整');
        return;
      }
      
      // 验证数据完整性
      const validateData = (indexData) => {
        if (!indexData || !Array.isArray(indexData.times) || !Array.isArray(indexData.prices)) {
          return false;
        }
        return indexData.times.length === indexData.prices.length;
      };
      
      // 处理每个指数的数据
      const processIndexData = (indexData) => {
        if (!validateData(indexData)) {
          return {
            times: [],
            prices: [],
            volumes: [],
            amounts: []
          };
        }
        
        return {
          times: indexData.times.map(time => time.split(' ')[1]), // 只保留时间部分
          prices: indexData.prices.map(price => parseFloat(price) || 0),
          volumes: indexData.volumes.map(vol => parseInt(vol) || 0),
          amounts: indexData.amounts.map(amt => parseFloat(amt) || 0)
        };
      };
      
      this.minData = {
        sh: processIndexData(data.sh),
        sz: processIndexData(data.sz),
        cyb: processIndexData(data.cyb)
      };
      
      // 更新图表
      this.$nextTick(() => {
        if (this.priceChart) {
          this.priceChart.setOption({
            xAxis: {
              data: this.minData.sh.times
            },
            series: [
              {
                name: '上证指数',
                data: this.minData.sh.prices
              },
              {
                name: '深证成指',
                data: this.minData.sz.prices
              },
              {
                name: '创业板指',
                data: this.minData.cyb.prices
              }
            ]
          });
        }
      });
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

.review-container {
  .review-section {
    margin-bottom: 20px;

    h3 {
      font-size: 16px;
      color: #303133;
      margin-bottom: 15px;
    }

    .review-content markdown-body {
      font-size: 14px;
      line-height: 1.8;
      color: #606266;

      h4 {
        font-size: 15px;
        color: #303133;
        margin: 15px 0 10px;
      }

      ul {
        padding-left: 20px;
        margin: 0;

        li {
          margin-bottom: 8px;

          &:last-child {
            margin-bottom: 0;
          }
        }
      }

      .highlight-text {
        color: #303133;
        font-weight: bold;
      }

      .up-trend {
        color: #f56c6c;
      }

      .down-trend {
        color: #67c23a;
      }

      .neutral-trend {
        color: #909399;
      }
    }
  }
}

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

.min-chart-container {
  height: 400px;
  margin-top: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.review-container {
  .review-section, .suggestion-section {
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

    .review-content, .suggestion-content {
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

      p {
        font-size: 14px;
        color: #606266;
        margin-bottom: 10px;
        line-height: 1.6;
      }

      ul {
        padding-left: 20px;
        margin-bottom: 15px;

        li {
          font-size: 14px;
          color: #606266;
          line-height: 1.8;
          margin-bottom: 8px;
        }
      }

      ol {
        padding-left: 20px;
        margin-bottom: 15px;

        li {
          font-size: 14px;
          color: #606266;
          line-height: 1.8;
          margin-bottom: 8px;
        }
      }

      strong {
        color: #303133;
        font-weight: bold;
      }

      .risk-warning {
        background-color: #fef0f0;
        padding: 15px;
        border-radius: 4px;
        border-left: 4px solid #f56c6c;

        ul {
          margin: 0;
          padding-left: 20px;

          li {
            color: #f56c6c;
          }
        }
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

  :deep(ol) {
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

  :deep(blockquote) {
    padding: 0 1em;
    color: #6a737d;
    border-left: 0.25em solid #dfe2e5;
    margin: 0 0 16px 0;
  }
}

.board-section {
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 15px;
    color: #303133;
  }
}

.fund-flow-section {
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 15px;
    color: #303133;
    display: flex;
    align-items: center;
    
    &::before {
      content: '';
      display: inline-block;
      width: 4px;
      height: 16px;
      background-color: #409eff;
      margin-right: 8px;
      border-radius: 2px;
    }
  }
}

.sector-name {
  display: flex;
  align-items: center;
  gap: 8px;

  .name {
    font-weight: 500;
    color: #303133;
  }
}

.fund-flow-value {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .el-progress {
    margin-top: 4px;
  }
}

.max-stock {
  display: flex;
  align-items: center;
  gap: 8px;

  .stock-name {
    font-weight: 500;
    color: #303133;
  }

  .stock-change {
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 2px;
    
    &.up {
      background-color: rgba(245, 108, 108, 0.1);
    }
    
    &.down {
      background-color: rgba(103, 194, 58, 0.1);
    }
  }
}

.limit-stocks-section {
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 15px;
    color: #303133;
    display: flex;
    align-items: center;
    gap: 8px;

    .up-icon {
      color: #f56c6c;
      font-size: 18px;
    }

    .down-icon {
      color: #67c23a;
      font-size: 18px;
    }

    .stock-count {
      font-size: 14px;
      color: #909399;
      font-weight: normal;
    }
  }

  .stock-code {
    font-family: monospace;
    color: #606266;
  }

  .stock-name {
    font-weight: 500;
    color: #303133;
  }

  .price {
    font-family: monospace;
    color: #606266;
  }

  :deep(.el-table) {
    .cell {
      white-space: nowrap;
    }
  }

  :deep(.el-table__row) {
    transition: all 0.3s;

    &:hover {
      background-color: #f5f7fa;
    }
  }

  :deep(.el-tag) {
    margin-right: 4px;
  }
}

.empty-data {
  text-align: center;
  padding: 20px;
  color: #909399;

  i {
    margin-right: 8px;
    font-size: 16px;
  }
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}

.inflow {
  color: #f56c6c;
}

.outflow {
  color: #67c23a;
}

.sentiment-indicator {
  text-align: center;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 10px;

  .indicator-name {
    font-size: 14px;
    color: #606266;
    margin-bottom: 8px;
  }

  .indicator-value {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 8px;

    &.extreme-hot { color: #f56c6c; }
    &.hot { color: #e6a23c; }
    &.neutral { color: #909399; }
    &.cold { color: #67c23a; }
    &.extreme-cold { color: #409eff; }

    &.extreme-fear { color: #f56c6c; }
    &.fear { color: #e6a23c; }
    &.greed { color: #67c23a; }
    &.extreme-greed { color: #409eff; }

    &.very-strong { color: #f56c6c; }
    &.strong { color: #e6a23c; }
    &.weak { color: #67c23a; }
    &.very-weak { color: #409eff; }

    &.strong-up { color: #f56c6c; }
    &.up { color: #e6a23c; }
    &.down { color: #67c23a; }
    &.strong-down { color: #409eff; }
  }

  .indicator-desc {
    font-size: 12px;
    color: #909399;
  }
}

.concept-item {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.5;
  padding: 10px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }

  &:last-child {
    margin-bottom: 0;
  }

  .concept-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .concept-info {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      min-width: 0;

      .label {
        color: #303133;
        font-weight: 500;
        white-space: nowrap;
      }

      .leader-stock {
        color: #909399;
        font-size: 12px;
        white-space: nowrap;
      }
    }

    .value {
      font-weight: bold;
      margin-left: 8px;
      white-space: nowrap;
    }
  }
}

:deep(.el-table) {
  .cell {
    white-space: normal;
    word-break: break-all;
    line-height: 1.5;
    padding: 8px;
  }

  .broker-name {
    .name-wrapper {
      display: flex;
      flex-direction: column;
      gap: 4px;
      
      .name {
        font-weight: bold;
        color: #303133;
        font-size: 14px;
        line-height: 1.5;
        word-break: break-all;
        white-space: normal;
        display: block;
        width: 100%;
        min-width: 400px;  /* 增加最小宽度 */
        overflow: visible;  /* 确保内容不会被截断 */
      }
    }
  }
}

:deep(.el-progress-bar__outer) {
  background-color: #f5f7fa;
}

:deep(.el-tag) {
  margin-right: 4px;
}

// 添加表格行样式
:deep(.el-table__row) {
  &.up-row {
    background-color: rgba(245, 108, 108, 0.05);
  }
  
  &.down-row {
    background-color: rgba(103, 194, 58, 0.05);
  }
}

.broker-name {
  display: flex;
  align-items: center;
  gap: 8px;

  .el-tag {
    margin-left: 4px;
  }
}

.broker-item {
  margin-bottom: 12px;
  padding: 8px;
  background-color: #f8f9fa;
  border-radius: 4px;
  
  .broker-name {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
    
    .name {
      font-weight: bold;
      color: #303133;
      font-size: 15px;
      line-height: 1.5;
      word-break: break-all;
      white-space: normal;
      display: block;
      width: 100%;
    }
  }
  
  .broker-info {
    font-size: 14px;
    color: #606266;
    line-height: 1.5;
    padding-left: 4px;
    word-break: break-all;
    white-space: normal;
  }
}

// 修改表格中的营业部名称显示
:deep(.el-table) {
  .broker-name {
    display: flex;
    flex-direction: column;
    gap: 4px;
    
    .name {
      font-weight: bold;
      color: #303133;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-all;
      white-space: normal;
      display: block;
      width: 100%;
    }
  }
}

.margin-account-section {
  margin-top: 20px;
  
  h3 {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 15px;
    color: #303133;
    display: flex;
    align-items: center;
    
    &::before {
      content: '';
      display: inline-block;
      width: 4px;
      height: 16px;
      background-color: #409eff;
      margin-right: 8px;
      border-radius: 2px;
    }
  }

  .margin-account-date {
    text-align: right;
    color: #909399;
    font-size: 14px;
    margin-bottom: 15px;
  }
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

.suggestion-content {
  .highlight-text {
    color: #f56c6c;
    font-weight: bold;
    font-size: 1.1em;
    background-color: rgba(245, 108, 108, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .important-suggestion {
    background-color: #fef0f0;
    border-left: 4px solid #f56c6c;
    padding: 12px 15px;
    margin: 10px 0;
    border-radius: 0 4px 4px 0;
    
    .suggestion-title {
      color: #f56c6c;
      font-weight: bold;
      margin-bottom: 8px;
      font-size: 15px;
    }
    
    .suggestion-content {
      color: #606266;
      line-height: 1.6;
    }
  }

  .risk-warning {
    background-color: #fef0f0;
    padding: 15px;
    border-radius: 4px;
    border-left: 4px solid #f56c6c;
    margin: 15px 0;

    .warning-title {
      color: #f56c6c;
      font-weight: bold;
      margin-bottom: 10px;
      font-size: 15px;
      display: flex;
      align-items: center;
      
      &::before {
        content: '⚠️';
        margin-right: 8px;
      }
    }

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

  .trend-analysis {
    background-color: #f0f9eb;
    padding: 12px 15px;
    margin: 10px 0;
    border-radius: 4px;
    border-left: 4px solid #67c23a;

    .trend-title {
      color: #67c23a;
      font-weight: bold;
      margin-bottom: 8px;
      font-size: 15px;
    }

    .trend-content {
      color: #606266;
      line-height: 1.6;
    }
  }

  .fund-analysis {
    background-color: #ecf5ff;
    padding: 12px 15px;
    margin: 10px 0;
    border-radius: 4px;
    border-left: 4px solid #409eff;

    .fund-title {
      color: #409eff;
      font-weight: bold;
      margin-bottom: 8px;
      font-size: 15px;
    }

    .fund-content {
      color: #606266;
      line-height: 1.6;
    }
  }

  .sector-opportunity {
    background-color: #fdf6ec;
    padding: 12px 15px;
    margin: 10px 0;
    border-radius: 4px;
    border-left: 4px solid #e6a23c;

    .opportunity-title {
      color: #e6a23c;
      font-weight: bold;
      margin-bottom: 8px;
      font-size: 15px;
    }

    .opportunity-content {
      color: #606266;
      line-height: 1.6;
    }
  }

  .key-point {
    font-weight: bold;
    color: #303133;
    background-color: #f5f7fa;
    padding: 2px 6px;
    border-radius: 4px;
    margin: 0 4px;
  }

  .data-highlight {
    font-family: 'DIN Condensed', 'Microsoft YaHei', sans-serif;
    font-weight: bold;
    color: #f56c6c;
    font-size: 1.1em;
  }

  .positive {
    color: #f56c6c;
    font-weight: 500;
  }

  .negative {
    color: #67c23a;
    font-weight: 500;
  }

  .neutral {
    color: #909399;
    font-weight: 500;
  }
}
</style> 
