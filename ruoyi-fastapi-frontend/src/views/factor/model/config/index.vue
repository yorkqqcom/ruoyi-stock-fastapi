<template>
  <div class="app-container">
    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Refresh" @click="getList" v-hasPermi="['factor:model:config:list']">刷新</el-button>
      </el-col>
      <right-toolbar @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="configList">
      <el-table-column label="配置名称" align="center" prop="name" :show-overflow-tooltip="true" />
      <el-table-column label="路径" align="center" prop="path" :show-overflow-tooltip="true" />
      <el-table-column label="因子数量" align="center" prop="factorCount" width="120" />
      <el-table-column label="操作" align="center" width="120" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="查看内容" placement="top">
            <el-button
              link
              type="primary"
              icon="View"
              @click="handleViewContent(scope.row)"
              v-hasPermi="['factor:model:config:list']"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && configList.length === 0" description="暂无因子配置文件，请在项目 config/train 目录下添加 .txt 文件" />

    <!-- 查看内容弹窗 -->
    <el-dialog title="因子列表内容" v-model="contentOpen" width="700px" append-to-body>
      <el-input
        v-model="contentFactorCodes"
        type="textarea"
        :rows="12"
        readonly
        placeholder="换行分隔的因子代码（每行一个）"
      />
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="contentOpen = false">关 闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="FactorConfig">
import { listFactorConfig, getFactorConfigContent } from '@/api/factor/config'

const { proxy } = getCurrentInstance()

const configList = ref([])
const loading = ref(true)
const contentOpen = ref(false)
const contentFactorCodes = ref('')

/** 查询因子配置文件列表 */
function getList() {
  loading.value = true
  listFactorConfig()
    .then((response) => {
      configList.value = response.data || []
      loading.value = false
    })
    .catch(() => {
      loading.value = false
    })
}

/** 查看内容 */
function handleViewContent(row) {
  getFactorConfigContent(row.path)
    .then((response) => {
      contentFactorCodes.value = response.data?.factorCodes || ''
      contentOpen.value = true
    })
    .catch(() => {
      proxy.$modal.msgError('获取配置内容失败')
    })
}

getList()
</script>
