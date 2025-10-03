# -- coding: utf-8 --
import akshare as ak
from fastapi import APIRouter, Request
from utils.response_util import ResponseUtil
from utils.log_util import logger
import pandas as pd
import numpy as np
from typing import Optional, Any

router = APIRouter(prefix="/api/concept", tags=["概念板块"])

def clean_nan_values(data: Any) -> Any:
    """
    递归清理数据中的NaN值，确保JSON序列化兼容
    
    Args:
        data: 需要清理的数据
        
    Returns:
        清理后的数据
    """
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, pd.Series):
        return data.replace({pd.NA: None, pd.NaT: None}).where(pd.notnull(data), None).tolist()
    elif isinstance(data, (np.floating, float)) and (np.isnan(data) or np.isinf(data)):
        return None
    elif isinstance(data, (np.integer, int)) and np.isnan(data):
        return None
    else:
        return data

@router.get("/board-list")
async def get_concept_board_list(request: Request):
    """
    获取东方财富概念板块列表
    """
    try:
        # 使用AKShare获取概念板块数据
        df = ak.stock_board_concept_name_em()
        
        # 转换DataFrame为字典列表，并清理NaN值
        data = df.to_dict(orient="records")
        data = clean_nan_values(data)
        
        logger.info(f"成功获取概念板块数据，共{len(data)}个板块")
        
        return ResponseUtil.success(data=data)
        
    except Exception as e:
        logger.error(f"获取概念板块列表失败: {e}")
        return ResponseUtil.error(msg=f"获取概念板块列表失败: {str(e)}")

@router.get("/component-stocks")
async def get_concept_component_stocks(
    symbol: str,
    request: Request
):
    """
    获取概念板块成分股
    """
    try:
        # 使用AKShare获取概念板块成分股数据
        df = ak.stock_board_concept_cons_em(symbol=symbol)
        
        # 转换DataFrame为字典列表，重命名字段以符合前端需求
        data = []
        for _, row in df.iterrows():
            item = {
                'symbol': row['代码'],
                'name': row['名称'],
                'price': row['最新价'],
                'change_pct': row['涨跌幅'],
                'change_amount': row['涨跌额']
            }
            data.append(item)
        
        # 清理NaN值，确保JSON序列化兼容
        data = clean_nan_values(data)
        
        logger.info(f"成功获取概念板块{symbol}成分股数据，共{len(data)}只股票")
        
        return ResponseUtil.success(data=data)
        
    except Exception as e:
        logger.error(f"获取概念板块{symbol}成分股失败: {e}")
        return ResponseUtil.error(msg=f"获取概念板块成分股失败: {str(e)}")

@router.get("/search")
async def search_concept_boards(
    keyword: str,
    request: Request
):
    """
    搜索概念板块
    """
    try:
        # 获取所有概念板块数据
        df = ak.stock_board_concept_name_em()
        
        # 根据关键词筛选
        if keyword:
            mask = df['板块名称'].str.contains(keyword, na=False)
            filtered_df = df[mask]
        else:
            filtered_df = df
        
        # 转换DataFrame为字典列表，并清理NaN值
        data = filtered_df.to_dict(orient="records")
        data = clean_nan_values(data)
        
        logger.info(f"搜索概念板块关键词'{keyword}'，找到{len(data)}个板块")
        
        return ResponseUtil.success(data=data)
        
    except Exception as e:
        logger.error(f"搜索概念板块失败: {e}")
        return ResponseUtil.error(msg=f"搜索概念板块失败: {str(e)}")
