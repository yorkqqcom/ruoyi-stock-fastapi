<template>
  <el-dialog
    :title="dialogTitle"
    :visible.sync="visible"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    @close="handleClose"
    class="param-config-dialog">
    
    <div class="dialog-content">
      <!-- 配置说明 -->
      <div class="config-info" v-if="configInfo">
        <el-alert
          :title="configInfo.name"
          :description="configInfo.description"
          type="info"
          :closable="false"
          show-icon>
        </el-alert>
      </div>

      <!-- 参数配置表单 -->
      <el-form
        ref="paramForm"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        size="small"
        class="param-form">
        
        <el-form-item
          v-for="param in requiredParams"
          :key="param.key"
          :label="param.title"
          :prop="param.key"
          :required="param.required">
          
          <!-- 下拉选择 -->
          <el-select
            v-if="param.options && param.options.length > 0"
            v-model="formData[param.key]"
            :placeholder="`请选择${param.title}`"
            style="width: 100%"
            clearable>
            <el-option
              v-for="option in param.options"
              :key="option.value"
              :label="option.label"
              :value="option.value">
            </el-option>
          </el-select>
          
          <!-- 日期选择 -->
          <el-date-picker
            v-else-if="param.type === 'date'"
            v-model="formData[param.key]"
            type="date"
            :placeholder="`请选择${param.title}`"
            style="width: 100%"
            format="yyyy-MM-dd"
            value-format="yyyy-MM-dd">
          </el-date-picker>
          
          <!-- 数字输入 -->
          <el-input-number
            v-else-if="param.type === 'number'"
            v-model="formData[param.key]"
            :placeholder="`请输入${param.title}`"
            style="width: 100%"
            :min="param.min"
            :max="param.max"
            :precision="param.precision || 0">
          </el-input-number>
          
          <!-- 文本输入 -->
          <el-input
            v-else
            v-model="formData[param.key]"
            :placeholder="`请输入${param.title}`"
            :type="param.type === 'password' ? 'password' : 'text'"
            :maxlength="param.maxlength"
            show-word-limit>
          </el-input>
          
          <!-- 参数说明 -->
          <div v-if="param.description" class="param-description">
            <i class="el-icon-info"></i>
            {{ param.description }}
          </div>
        </el-form-item>

        <!-- 可选参数折叠区域 -->
        <el-collapse v-if="optionalParams.length > 0" class="optional-params">
          <el-collapse-item title="可选参数" name="optional">
            <template slot="title">
              <span>可选参数</span>
              <el-tag size="mini" type="info" style="margin-left: 8px;">
                {{ optionalParams.length }}个
              </el-tag>
            </template>
            
            <el-form-item
              v-for="param in optionalParams"
              :key="param.key"
              :label="param.title"
              :prop="param.key">
              
              <!-- 下拉选择 -->
              <el-select
                v-if="param.options && param.options.length > 0"
                v-model="formData[param.key]"
                :placeholder="`请选择${param.title}`"
                style="width: 100%"
                clearable>
                <el-option
                  v-for="option in param.options"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value">
                </el-option>
              </el-select>
              
              <!-- 日期选择 -->
              <el-date-picker
                v-else-if="param.type === 'date'"
                v-model="formData[param.key]"
                type="date"
                :placeholder="`请选择${param.title}`"
                style="width: 100%"
                format="yyyy-MM-dd"
                value-format="yyyy-MM-dd">
              </el-date-picker>
              
              <!-- 数字输入 -->
              <el-input-number
                v-else-if="param.type === 'number'"
                v-model="formData[param.key]"
                :placeholder="`请输入${param.title}`"
                style="width: 100%"
                :min="param.min"
                :max="param.max"
                :precision="param.precision || 0">
              </el-input-number>
              
              <!-- 文本输入 -->
              <el-input
                v-else
                v-model="formData[param.key]"
                :placeholder="`请输入${param.title}`"
                :type="param.type === 'password' ? 'password' : 'text'"
                :maxlength="param.maxlength"
                show-word-limit>
              </el-input>
              
              <!-- 参数说明 -->
              <div v-if="param.description" class="param-description">
                <i class="el-icon-info"></i>
                {{ param.description }}
              </div>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </div>

    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose" size="small">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleConfirm" 
        size="small"
        :loading="loading">
        确定
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'ParamConfigDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    configInfo: {
      type: Object,
      default: null
    },
    params: {
      type: Array,
      default: () => []
    },
    initialValues: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      formData: {},
      formRules: {},
      loading: false
    }
  },
  computed: {
    dialogTitle() {
      if (this.configInfo) {
        return `配置参数 - ${this.configInfo.name}`
      }
      return '参数配置'
    },
    requiredParams() {
      return this.params.filter(param => param.required === true)
    },
    optionalParams() {
      return this.params.filter(param => param.required !== true)
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.initForm()
      }
    },
    params: {
      handler() {
        if (this.visible) {
          this.initForm()
        }
      },
      deep: true
    }
  },
  methods: {
    initForm() {
      // 初始化表单数据
      this.formData = { ...this.initialValues }
      this.formRules = {}
      
      // 为每个参数设置默认值和验证规则
      this.params.forEach(param => {
        // 设置默认值
        if (this.formData[param.key] === undefined) {
          if (param.default !== undefined) {
            this.formData[param.key] = param.default
          } else if (param.options && param.options.length > 0) {
            this.formData[param.key] = param.options[0].value
          } else {
            this.formData[param.key] = ''
          }
        }
        
        // 设置验证规则
        if (param.required) {
          this.formRules[param.key] = [
            { required: true, message: `请选择${param.title}`, trigger: 'change' }
          ]
        }
        
        // 添加类型验证
        if (param.type === 'number') {
          const rules = this.formRules[param.key] || []
          rules.push({
            validator: (rule, value, callback) => {
              if (value !== '' && value !== null && value !== undefined) {
                if (isNaN(value)) {
                  callback(new Error('请输入有效的数字'))
                } else {
                  if (param.min !== undefined && value < param.min) {
                    callback(new Error(`数值不能小于${param.min}`))
                  } else if (param.max !== undefined && value > param.max) {
                    callback(new Error(`数值不能大于${param.max}`))
                  } else {
                    callback()
                  }
                }
              } else {
                callback()
              }
            },
            trigger: 'blur'
          })
          this.formRules[param.key] = rules
        }
      })
    },
    
    handleClose() {
      this.$emit('close')
    },
    
    async handleConfirm() {
      try {
        // 验证表单
        await this.$refs.paramForm.validate()
        
        this.loading = true
        
        // 过滤掉空值，只返回有值的参数
        const validParams = {}
        Object.keys(this.formData).forEach(key => {
          const value = this.formData[key]
          if (value !== '' && value !== null && value !== undefined) {
            validParams[key] = value
          }
        })
        
        // 触发确认事件，传递配置好的参数
        this.$emit('confirm', {
          configKey: this.configInfo?.key,
          params: validParams,
          configInfo: this.configInfo
        })
        
        this.loading = false
        this.handleClose()
        
      } catch (error) {
        this.loading = false
        console.error('表单验证失败:', error)
        this.$message.error('请检查参数配置')
      }
    }
  }
}
</script>

<style scoped>
.param-config-dialog .el-dialog__body {
  padding: 20px;
}

.dialog-content {
  max-height: 60vh;
  overflow-y: auto;
}

.config-info {
  margin-bottom: 20px;
}

.param-form {
  margin-top: 20px;
}

.param-description {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
}

.param-description i {
  margin-right: 4px;
  color: #409eff;
}

.optional-params {
  margin-top: 20px;
}

.optional-params .el-collapse-item__header {
  background: #f8f9fa;
  padding-left: 12px;
  font-weight: 500;
}

.optional-params .el-collapse-item__content {
  padding: 16px 12px;
  background: #fafbfc;
}

.dialog-footer {
  text-align: right;
  padding: 10px 20px;
  border-top: 1px solid #ebeef5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .param-config-dialog {
    width: 95% !important;
  }
  
  .param-form .el-form-item__label {
    width: 100px !important;
  }
}
</style>
