<template>
  <div class="property-panel">
    <el-form :model="formData" label-width="100px" size="small">
      <!-- 节点属性 -->
      <template v-if="elementType === 'node'">
        <el-form-item label="步骤名称">
          <el-input v-model="formData.stepName" placeholder="请输入步骤名称" @blur="handleUpdate" />
        </el-form-item>

        <el-form-item label="节点类型">
          <el-select v-model="formData.nodeType" disabled>
            <el-option label="开始节点" value="start" />
            <el-option label="任务节点" value="task" />
            <el-option label="结束节点" value="end" />
          </el-select>
        </el-form-item>

        <el-form-item label="接口配置" v-if="formData.nodeType === 'task'">
          <el-select 
            v-model="formData.configId" 
            placeholder="请选择接口配置"
            filterable
            @change="handleUpdate"
          >
            <el-option
              v-for="config in apiConfigs"
              :key="config.configId"
              :label="config.apiName"
              :value="config.configId"
            >
              <span>{{ config.apiName }}</span>
              <span style="color: #8492a6; font-size: 13px; margin-left: 10px">{{ config.apiCode }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="遍历模式" v-if="formData.nodeType === 'task'">
          <el-switch
            v-model="formData.loopMode"
            active-value="1"
            inactive-value="0"
            active-text="开启"
            inactive-text="关闭"
            @change="handleUpdate"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            开启后，所有变量参数（${...}格式）都会从前一步的所有记录中遍历执行
          </div>
        </el-form-item>

        <el-form-item label="步骤参数">
          <el-input
            v-model="formData.stepParams"
            type="textarea"
            :rows="5"
            placeholder='请输入JSON格式参数，支持三种格式：&#10;1. 固定值：{"ts_code": "000001.SZ"}&#10;2. 变量（第一条记录）：{"ts_code": "${previous_step.ts_code}"}&#10;3. 遍历变量：{"ts_code": {"type": "loop", "source": "previous_step.ts_code"}}'
            @blur="handleUpdate"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            <div><strong>参数格式说明：</strong></div>
            <div>• <strong>固定值</strong>：直接使用配置的值，例如：{"ts_code": "000001.SZ"}</div>
            <div>• <strong>变量</strong>：从前一步第一条记录获取，例如：{"ts_code": "${previous_step.ts_code}"}</div>
            <div>• <strong>遍历变量</strong>：从前一步所有记录遍历（开启遍历模式时，${...}格式会自动转换为遍历变量）</div>
            <div>• <strong>对象格式</strong>：{"ts_code": {"type": "loop", "source": "previous_step.ts_code"}} 显式指定遍历</div>
            <div style="margin-top: 5px; color: #E6A23C;">
              <strong>注意：</strong>多个遍历参数会生成笛卡尔积组合（如：3个股票 × 2个日期 = 6次调用）
            </div>
          </div>
        </el-form-item>

        <el-form-item label="执行条件">
          <el-input
            v-model="formData.conditionExpr"
            type="textarea"
            :rows="2"
            placeholder='请输入执行条件表达式'
            @blur="handleUpdate"
          />
        </el-form-item>

        <el-form-item label="数据表名" v-if="formData.nodeType === 'task'">
          <el-input 
            v-model="formData.dataTableName" 
            placeholder="留空则使用默认表名（tushare_接口代码）" 
            @blur="handleUpdate"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            留空则自动使用 tushare_接口代码 作为表名。流程配置模式下，每个步骤默认使用各自的接口代码作为表名，也可在此为当前步骤单独指定表名
          </div>
        </el-form-item>

        <el-form-item label="数据更新方式" v-if="formData.nodeType === 'task'">
          <el-select 
            v-model="formData.updateMode" 
            placeholder="请选择数据更新方式"
            @change="handleUpdate"
          >
            <el-option label="仅插入（遇到重复会报错）" value="0" />
            <el-option label="忽略重复（静默跳过）" value="1" />
            <el-option label="存在则更新，不存在则插入" value="2" />
            <el-option label="先删除再插入（全量替换）" value="3" />
          </el-select>
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            <div><strong>更新方式说明：</strong></div>
            <div>• <strong>仅插入</strong>：直接插入数据，遇到重复键会报错</div>
            <div>• <strong>忽略重复</strong>：遇到重复数据时静默跳过，不报错</div>
            <div>• <strong>存在则更新</strong>：如果数据已存在（根据唯一键判断），则更新；不存在则插入</div>
            <div>• <strong>先删除再插入</strong>：先删除匹配的记录，再插入新数据，用于全量替换</div>
            <div style="margin-top: 5px; color: #E6A23C;">
              <strong>注意：</strong>后两种模式需要唯一键字段，如果未配置则自动检测表的主键或唯一索引
            </div>
          </div>
        </el-form-item>

        <el-form-item label="唯一键字段" v-if="formData.nodeType === 'task'">
          <el-input
            v-model="formData.uniqueKeyFields"
            type="textarea"
            :rows="2"
            placeholder='请输入JSON格式的唯一键字段数组，例如：["ts_code", "trade_date"]&#10;留空则自动检测表的主键或唯一索引'
            @blur="handleUpdate"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            <div><strong>唯一键字段说明：</strong></div>
            <div>• 用于判断数据是否重复的字段组合</div>
            <div>• 格式：JSON数组，例如：["ts_code", "trade_date"]</div>
            <div>• 留空则自动检测表的主键或唯一索引</div>
            <div>• 仅在"存在则更新"和"先删除再插入"模式下需要</div>
          </div>
        </el-form-item>

        <el-form-item label="位置坐标">
          <el-row :gutter="8">
            <el-col :span="12">
              <el-input-number
                v-model="formData.positionX"
                :min="0"
                :step="10"
                placeholder="X"
                @change="handleUpdate"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="12">
              <el-input-number
                v-model="formData.positionY"
                :min="0"
                :step="10"
                placeholder="Y"
                @change="handleUpdate"
                style="width: 100%"
              />
            </el-col>
          </el-row>
        </el-form-item>
      </template>

      <!-- 连接线属性 -->
      <template v-if="elementType === 'edge'">
        <el-form-item label="条件表达式">
          <el-input
            v-model="formData.label"
            type="textarea"
            :rows="2"
            placeholder='请输入条件表达式，例如：status == "success"'
            @blur="handleUpdate"
          />
        </el-form-item>

        <el-form-item label="源节点">
          <el-input :value="element.source" disabled />
        </el-form-item>

        <el-form-item label="目标节点">
          <el-input :value="element.target" disabled />
        </el-form-item>
      </template>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  element: {
    type: Object,
    required: true
  },
  elementType: {
    type: String,
    required: true // 'node' | 'edge'
  },
  apiConfigs: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update'])

const formData = ref({})

// 初始化表单数据
watch(() => props.element, (newElement) => {
  if (props.elementType === 'node') {
    // 处理唯一键字段：如果是对象，转换为JSON字符串；如果是字符串，直接使用
    let uniqueKeyFields = newElement.data?.uniqueKeyFields || ''
    if (uniqueKeyFields && typeof uniqueKeyFields === 'object') {
      try {
        uniqueKeyFields = JSON.stringify(uniqueKeyFields)
      } catch (e) {
        uniqueKeyFields = ''
      }
    }
    
    formData.value = {
      stepName: newElement.data?.stepName || '',
      nodeType: newElement.type || 'task',
      configId: newElement.data?.configId || null,
      stepParams: newElement.data?.stepParams || '',
      conditionExpr: newElement.data?.conditionExpr || '',
      dataTableName: newElement.data?.dataTableName || '',
      loopMode: newElement.data?.loopMode || '0',
      updateMode: newElement.data?.updateMode || '0',
      uniqueKeyFields: uniqueKeyFields,
      positionX: Math.round(newElement.position?.x || 0),
      positionY: Math.round(newElement.position?.y || 0)
    }
  } else if (props.elementType === 'edge') {
    formData.value = {
      label: newElement.label || ''
    }
  }
}, { immediate: true })

// 更新属性
function handleUpdate() {
  if (props.elementType === 'node') {
    // 验证唯一键字段格式
    let uniqueKeyFields = formData.value.uniqueKeyFields || ''
    if (uniqueKeyFields && uniqueKeyFields.trim()) {
      try {
        const parsed = JSON.parse(uniqueKeyFields)
        if (!Array.isArray(parsed)) {
          throw new Error('唯一键字段必须是JSON数组格式')
        }
        // 验证通过，保持原值
      } catch (e) {
        // 格式错误，清空或提示
        console.warn('唯一键字段格式错误，将使用空值:', e)
        uniqueKeyFields = ''
      }
    }
    
    const updates = {
      stepName: formData.value.stepName,
      configId: formData.value.configId,
      stepParams: formData.value.stepParams,
      conditionExpr: formData.value.conditionExpr,
      dataTableName: formData.value.dataTableName,
      loopMode: formData.value.loopMode,
      updateMode: formData.value.updateMode,
      uniqueKeyFields: uniqueKeyFields
    }
    
    // 更新位置
    if (props.element.position) {
      props.element.position.x = formData.value.positionX
      props.element.position.y = formData.value.positionY
    }
    
    emit('update', updates)
  } else if (props.elementType === 'edge') {
    emit('update', {
      label: formData.value.label
    })
  }
}
</script>

<style scoped lang="scss">
.property-panel {
  padding: 16px;

  :deep(.el-form-item) {
    margin-bottom: 18px;
  }

  :deep(.el-form-item__label) {
    font-size: 13px;
    color: #606266;
  }
}
</style>
