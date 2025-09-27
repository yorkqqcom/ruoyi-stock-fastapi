// EDE 增强配置：支持多个指标接口的树形结构
// 此文件由脚本自动生成，请勿手动修改
// 源文件: shared-config/ede_config.json

export default {
  "ede_yysj_em": {
    "key": "ede_yysj_em",
    "name": "预约披露时间",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-预约披露时间",
    "akshare": {
      "method": "stock_yysj_em",
      "params": {
        "symbol": {
          "type": "string",
          "required": true,
          "title": "市场板块",
          "description": "选择要查询的市场板块",
          "options": [
            {
              "value": "沪深A股",
              "label": "沪深A股"
            },
            {
              "value": "沪市A股",
              "label": "沪市A股"
            },
            {
              "value": "科创板",
              "label": "科创板"
            },
            {
              "value": "深市A股",
              "label": "深市A股"
            },
            {
              "value": "创业板",
              "label": "创业板"
            },
            {
              "value": "京市A股",
              "label": "京市A股"
            },
            {
              "value": "ST板",
              "label": "ST板"
            }
          ]
        },
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20251231",
              "label": "2025年四季度"
            },
            {
              "value": "20250930",
              "label": "2025年三季度"
            },
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "首次预约时间": "first_appointment_time",
        "一次变更日期": "first_change_date",
        "二次变更日期": "second_change_date",
        "三次变更日期": "third_change_date",
        "实际披露时间": "actual_disclosure_time"
      }
    },
    "ui": {
      "form": [
        "symbol",
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "first_appointment_time",
          "label": "首次预约时间",
          "width": 120
        },
        {
          "field": "first_change_date",
          "label": "一次变更日期",
          "width": 120
        },
        {
          "field": "second_change_date",
          "label": "二次变更日期",
          "width": 120
        },
        {
          "field": "third_change_date",
          "label": "三次变更日期",
          "width": 120
        },
        {
          "field": "actual_disclosure_time",
          "label": "实际披露时间",
          "width": 120
        }
      ]
    }
  },
  "ede_yjyg_em": {
    "key": "ede_yjyg_em",
    "name": "业绩预告",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-业绩预告",
    "akshare": {
      "method": "stock_yjyg_em",
      "params": {
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "预测指标": "forecast_indicator",
        "业绩变动": "performance_change",
        "预测数值": "forecast_value",
        "业绩变动幅度": "change_ratio",
        "业绩变动原因": "change_reason",
        "预告类型": "forecast_type",
        "上年同期值": "last_year_value",
        "公告日期": "announcement_date"
      }
    },
    "ui": {
      "form": [
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "forecast_indicator",
          "label": "预测指标",
          "width": 120
        },
        {
          "field": "performance_change",
          "label": "业绩变动",
          "width": 100
        },
        {
          "field": "forecast_value",
          "label": "预测数值(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "change_ratio",
          "label": "变动幅度(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "change_reason",
          "label": "变动原因",
          "width": 150
        },
        {
          "field": "forecast_type",
          "label": "预告类型",
          "width": 100
        },
        {
          "field": "last_year_value",
          "label": "上年同期(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "announcement_date",
          "label": "公告日期",
          "width": 120
        }
      ]
    }
  },
  "ede_yjkb_em": {
    "key": "ede_yjkb_em",
    "name": "业绩快报",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-业绩快报",
    "akshare": {
      "method": "stock_yjkb_em",
      "params": {
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "每股收益": "eps",
        "营业收入": "revenue",
        "营业收入上年同期": "revenue_last_year",
        "营业收入同比增长": "revenue_growth_yoy",
        "营业收入季度环比": "revenue_growth_qoq",
        "净利润": "net_profit",
        "净利润上年同期": "profit_last_year",
        "净利润同比增长": "profit_growth_yoy",
        "净利润季度环比": "profit_growth_qoq",
        "每股净资产": "bps",
        "净资产收益率": "roe",
        "所处行业": "industry",
        "最新公告日期": "announcement_date",
        "所属板块": "market_board",
        "证券类型": "security_type"
      }
    },
    "ui": {
      "form": [
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "eps",
          "label": "每股收益",
          "align": "right",
          "width": 100
        },
        {
          "field": "revenue",
          "label": "营业收入",
          "align": "right",
          "width": 120
        },
        {
          "field": "revenue_growth_yoy",
          "label": "营收同比增长(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "net_profit",
          "label": "净利润",
          "align": "right",
          "width": 120
        },
        {
          "field": "profit_growth_yoy",
          "label": "净利润同比增长(%)",
          "align": "right",
          "width": 130
        },
        {
          "field": "roe",
          "label": "净资产收益率(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "industry",
          "label": "所处行业",
          "width": 120
        },
        {
          "field": "announcement_date",
          "label": "公告日期",
          "width": 120
        }
      ]
    }
  },
  "ede_yjbb_em": {
    "key": "ede_yjbb_em",
    "name": "业绩报表",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-业绩报表",
    "akshare": {
      "method": "stock_yjbb_em",
      "params": {
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "每股收益": "eps",
        "营业总收入-营业总收入": "total_revenue",
        "营业总收入-同比增长": "revenue_growth_yoy",
        "营业总收入-季度环比增长": "revenue_growth_qoq",
        "净利润-净利润": "net_profit",
        "净利润-同比增长": "profit_growth_yoy",
        "净利润-季度环比增长": "profit_growth_qoq",
        "每股净资产": "bps",
        "净资产收益率": "roe",
        "每股经营现金流量": "cfps",
        "销售毛利率": "gross_margin",
        "所处行业": "industry",
        "最新公告日期": "announcement_date"
      }
    },
    "ui": {
      "form": [
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "eps",
          "label": "每股收益(元)",
          "align": "right",
          "width": 100
        },
        {
          "field": "total_revenue",
          "label": "营业总收入(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "revenue_growth_yoy",
          "label": "营收同比增长(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "revenue_growth_qoq",
          "label": "营收季度环比(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "net_profit",
          "label": "净利润(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "profit_growth_yoy",
          "label": "净利润同比增长(%)",
          "align": "right",
          "width": 130
        },
        {
          "field": "profit_growth_qoq",
          "label": "净利润季度环比(%)",
          "align": "right",
          "width": 130
        },
        {
          "field": "bps",
          "label": "每股净资产(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "roe",
          "label": "净资产收益率(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "cfps",
          "label": "每股经营现金流量(元)",
          "align": "right",
          "width": 140
        },
        {
          "field": "gross_margin",
          "label": "销售毛利率(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "industry",
          "label": "所处行业",
          "width": 120
        },
        {
          "field": "announcement_date",
          "label": "最新公告日期",
          "width": 120
        }
      ]
    }
  },
  "ede_lrb_em": {
    "key": "ede_lrb_em",
    "name": "利润表",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-业绩快报-利润表",
    "akshare": {
      "method": "stock_lrb_em",
      "params": {
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "净利润": "net_profit",
        "净利润同比": "net_profit_growth_yoy",
        "营业总收入": "total_revenue",
        "营业总收入同比": "total_revenue_growth_yoy",
        "营业支出": "operating_expenses",
        "销售费用": "sales_expenses",
        "管理费用": "management_expenses",
        "财务费用": "financial_expenses",
        "营业支出合计": "total_operating_expenses",
        "营业利润": "operating_profit",
        "利润总额": "total_profit",
        "最新公告日期": "announcement_date"
      }
    },
    "ui": {
      "form": [
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "net_profit",
          "label": "净利润(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "net_profit_growth_yoy",
          "label": "净利润同比(%)",
          "align": "right",
          "width": 120
        },
        {
          "field": "total_revenue",
          "label": "营业总收入(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "total_revenue_growth_yoy",
          "label": "营业总收入同比(%)",
          "align": "right",
          "width": 140
        },
        {
          "field": "operating_expenses",
          "label": "营业支出(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "sales_expenses",
          "label": "销售费用(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "management_expenses",
          "label": "管理费用(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "financial_expenses",
          "label": "财务费用(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "operating_profit",
          "label": "营业利润(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "total_profit",
          "label": "利润总额(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "announcement_date",
          "label": "公告日期",
          "width": 120
        }
      ]
    }
  },
  "ede_xjll_em": {
    "key": "ede_xjll_em",
    "name": "现金流量表",
    "category": "财务数据",
    "description": "东方财富-数据中心-年报季报-业绩快报-现金流量表",
    "akshare": {
      "method": "stock_xjll_em",
      "params": {
        "date": {
          "type": "string",
          "required": true,
          "title": "报告期",
          "description": "选择要查询的财务报告期",
          "options": [
            {
              "value": "20250630",
              "label": "2025年二季度"
            },
            {
              "value": "20250331",
              "label": "2025年一季度"
            },
            {
              "value": "20241231",
              "label": "2024年四季度"
            },
            {
              "value": "20240930",
              "label": "2024年三季度"
            },
            {
              "value": "20240630",
              "label": "2024年二季度"
            },
            {
              "value": "20240331",
              "label": "2024年一季度"
            },
            {
              "value": "20231231",
              "label": "2023年四季度"
            },
            {
              "value": "20230930",
              "label": "2023年三季度"
            },
            {
              "value": "20230630",
              "label": "2023年二季度"
            },
            {
              "value": "20230331",
              "label": "2023年一季度"
            }
          ]
        }
      }
    },
    "mapping": {
      "fields": {
        "序号": "index",
        "股票代码": "symbol",
        "股票简称": "name",
        "净现金流-净现金流": "net_cash_flow",
        "净现金流-同比增长": "net_cash_flow_growth_yoy",
        "经营性现金流-现金流量净额": "operating_cash_flow",
        "经营性现金流-净现金流占比": "operating_cash_flow_ratio",
        "投资性现金流-现金流量净额": "investing_cash_flow",
        "投资性现金流-净现金流占比": "investing_cash_flow_ratio",
        "融资性现金流-现金流量净额": "financing_cash_flow",
        "融资性现金流-净现金流占比": "financing_cash_flow_ratio",
        "公告日期": "announcement_date"
      }
    },
    "ui": {
      "form": [
        "date"
      ],
      "columns": [
        {
          "field": "symbol",
          "label": "股票代码",
          "width": 100
        },
        {
          "field": "name",
          "label": "股票名称",
          "width": 120
        },
        {
          "field": "net_cash_flow",
          "label": "净现金流(元)",
          "align": "right",
          "width": 120
        },
        {
          "field": "net_cash_flow_growth_yoy",
          "label": "净现金流同比(%)",
          "align": "right",
          "width": 130
        },
        {
          "field": "operating_cash_flow",
          "label": "经营性现金流(元)",
          "align": "right",
          "width": 140
        },
        {
          "field": "operating_cash_flow_ratio",
          "label": "经营性现金流占比(%)",
          "align": "right",
          "width": 150
        },
        {
          "field": "investing_cash_flow",
          "label": "投资性现金流(元)",
          "align": "right",
          "width": 140
        },        {
          "field": "investing_cash_flow_ratio",
          "label": "投资性现金流占比(%)",
          "align": "right",
          "width": 150
        },
        {
          "field": "financing_cash_flow",
          "label": "融资性现金流(元)",
          "align": "right",
          "width": 140
        },
        {
          "field": "financing_cash_flow_ratio",
          "label": "融资性现金流占比(%)",
          "align": "right",
          "width": 150
        },
        {
          "field": "announcement_date",
          "label": "公告日期",
          "width": 120
        }
      ]
    }
  }
}

// 指标分类树结构配置（由共享配置按 category 动态生成）
export const METRIC_CATEGORIES = {
  "财务数据": {
    "icon": "el-icon-document",
    "children": [
      "ede_yysj_em",
      "ede_yjyg_em",
      "ede_yjkb_em",
      "ede_yjbb_em",
      "ede_lrb_em",
      "ede_xjll_em"
    ]
  }
}

// 默认选中的指标配置（可按需在前端覆盖）
export const DEFAULT_SELECTED_METRICS = {
  "ede_yjbb_em": ["eps", "total_revenue", "net_profit", "roe"],
  "ede_yjkb_em": ["eps", "revenue", "net_profit", "roe"],
  "ede_yjyg_em": ["forecast_value", "change_ratio", "forecast_type"]
}
