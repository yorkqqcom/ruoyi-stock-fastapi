#!/usr/bin/env node

/**
 * 配置同步脚本
 * 将共享配置文件同步到前端和后端
 */

const fs = require('fs');
const path = require('path');

const SHARED_CONFIG_PATH = path.join(__dirname, '..', 'shared-config', 'ede_config.json');
const FRONTEND_CONFIG_PATH = path.join(__dirname, '..', 'ruoyi-fastapi-frontend', 'src', 'views', 'stock', 'ede', 'enhanced-config.js');
const BACKEND_CONFIG_PATH = path.join(__dirname, '..', 'ruoyi-fastapi-backend', 'user_module', 'config', 'ede_config.json');

function syncConfig() {
  console.log('🔄 开始同步配置文件...');
  
  // 检查共享配置文件是否存在
  if (!fs.existsSync(SHARED_CONFIG_PATH)) {
    console.error('❌ 共享配置文件不存在:', SHARED_CONFIG_PATH);
    process.exit(1);
  }
  
  try {
    // 读取共享配置
    const sharedConfig = JSON.parse(fs.readFileSync(SHARED_CONFIG_PATH, 'utf8'));
    console.log('✅ 成功读取共享配置文件');
    
    // 同步到后端
    if (fs.existsSync(path.dirname(BACKEND_CONFIG_PATH))) {
      fs.writeFileSync(BACKEND_CONFIG_PATH, JSON.stringify(sharedConfig, null, 2));
      console.log('✅ 已同步到后端配置文件:', BACKEND_CONFIG_PATH);
    } else {
      console.warn('⚠️  后端配置目录不存在:', path.dirname(BACKEND_CONFIG_PATH));
    }
    
    // 生成前端JavaScript配置文件
    const jsConfig = generateFrontendConfig(sharedConfig);
    if (fs.existsSync(path.dirname(FRONTEND_CONFIG_PATH))) {
      fs.writeFileSync(FRONTEND_CONFIG_PATH, jsConfig);
      console.log('✅ 已同步到前端配置文件:', FRONTEND_CONFIG_PATH);
    } else {
      console.warn('⚠️  前端配置目录不存在:', path.dirname(FRONTEND_CONFIG_PATH));
    }
    
    console.log('🎉 配置同步完成！');
    
  } catch (error) {
    console.error('❌ 配置同步失败:', error.message);
    process.exit(1);
  }
}

function generateFrontendConfig(config) {
  // 按共享配置中的 category 字段动态分组，生成前端分类树
  const categoryToKeys = {};
  Object.entries(config || {}).forEach(([key, value]) => {
    const category = (value && value.category) || '未分类';
    if (!categoryToKeys[category]) {
      categoryToKeys[category] = [];
    }
    categoryToKeys[category].push(key);
  });

  // 组装前端需要的结构：每个分类附带图标与 children
  const METRIC_CATEGORIES = {};
  Object.entries(categoryToKeys).forEach(([cat, keys]) => {
    METRIC_CATEGORIES[cat] = {
      icon: 'el-icon-document',
      children: keys
    };
  });

  const jsContent = `// EDE 增强配置：支持多个指标接口的树形结构
// 此文件由脚本自动生成，请勿手动修改
// 源文件: shared-config/ede_config.json

export default ${JSON.stringify(config, null, 2)}

// 指标分类树结构配置（由共享配置按 category 动态生成）
export const METRIC_CATEGORIES = ${JSON.stringify(METRIC_CATEGORIES, null, 2)}

// 默认选中的指标配置（可按需在前端覆盖）
export const DEFAULT_SELECTED_METRICS = {
  "ede_yjbb_em": ["eps", "total_revenue", "net_profit", "roe"],
  "ede_yjkb_em": ["eps", "revenue", "net_profit", "roe"],
  "ede_yjyg_em": ["forecast_value", "change_ratio", "forecast_type"]
}
`;

  return jsContent;
}

// 如果直接运行此脚本
if (require.main === module) {
  syncConfig();
}

module.exports = { syncConfig, generateFrontendConfig };
