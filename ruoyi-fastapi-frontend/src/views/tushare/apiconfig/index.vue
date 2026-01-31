<template>
   <div class="app-container">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
         <el-form-item label="接口名称" prop="apiName">
            <el-input
               v-model="queryParams.apiName"
               placeholder="请输入接口名称"
               clearable
               style="width: 200px"
               @keyup.enter="handleQuery"
            />
         </el-form-item>
         <el-form-item label="接口代码" prop="apiCode">
            <el-input
               v-model="queryParams.apiCode"
               placeholder="请输入接口代码"
               clearable
               style="width: 200px"
               @keyup.enter="handleQuery"
            />
         </el-form-item>
         <el-form-item label="状态" prop="status">
            <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 200px">
               <el-option
                  v-for="dict in sys_normal_disable"
                  :key="dict.value"
                  :label="dict.label"
                  :value="dict.value"
               />
            </el-select>
         </el-form-item>
         <el-form-item>
            <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
            <el-button icon="Refresh" @click="resetQuery">重置</el-button>
         </el-form-item>
      </el-form>

      <el-row :gutter="10" class="mb8">
         <el-col :span="1.5">
            <el-button
               type="primary"
               plain
               icon="Plus"
               @click="handleAdd"
               v-hasPermi="['tushare:apiConfig:add']"
            >新增</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="success"
               plain
               icon="Edit"
               :disabled="single"
               @click="handleUpdate"
               v-hasPermi="['tushare:apiConfig:edit']"
            >修改</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="danger"
               plain
               icon="Delete"
               :disabled="multiple"
               @click="handleDelete"
               v-hasPermi="['tushare:apiConfig:remove']"
            >删除</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="warning"
               plain
               icon="Download"
               @click="handleExport"
               v-hasPermi="['tushare:apiConfig:export']"
            >导出</el-button>
         </el-col>
         <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
      </el-row>

      <el-table v-loading="loading" :data="apiConfigList" @selection-change="handleSelectionChange">
         <el-table-column type="selection" width="55" align="center" />
         <el-table-column label="配置ID" width="100" align="center" prop="configId" />
         <el-table-column label="接口名称" align="center" prop="apiName" :show-overflow-tooltip="true" />
         <el-table-column label="接口代码" align="center" prop="apiCode" :show-overflow-tooltip="true" />
         <el-table-column label="接口描述" align="center" prop="apiDesc" :show-overflow-tooltip="true" />
         <el-table-column label="状态" align="center">
            <template #default="scope">
               <el-switch
                  v-model="scope.row.status"
                  active-value="0"
                  inactive-value="1"
                  @change="handleStatusChange(scope.row)"
               ></el-switch>
            </template>
         </el-table-column>
         <el-table-column label="创建时间" align="center" prop="createTime" width="180">
            <template #default="scope">
               <span>{{ parseTime(scope.row.createTime) }}</span>
            </template>
         </el-table-column>
         <el-table-column label="操作" align="center" width="200" class-name="small-padding fixed-width">
            <template #default="scope">
               <el-tooltip content="修改" placement="top">
                  <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['tushare:apiConfig:edit']"></el-button>
               </el-tooltip>
               <el-tooltip content="删除" placement="top">
                  <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['tushare:apiConfig:remove']"></el-button>
               </el-tooltip>
            </template>
         </el-table-column>
      </el-table>

      <pagination
         v-show="total > 0"
         :total="total"
         v-model:page="queryParams.pageNum"
         v-model:limit="queryParams.pageSize"
         @pagination="getList"
      />

      <!-- 添加或修改接口配置对话框 -->
      <el-dialog :title="title" v-model="open" width="900px" append-to-body>
         <el-form ref="apiConfigRef" :model="form" :rules="rules" label-width="120px">
            <!-- 隐藏字段：确保configId被包含在表单中 -->
            <el-form-item v-if="form.configId" style="display: none;">
               <el-input v-model="form.configId" type="hidden" />
            </el-form-item>
            <el-row>
               <el-col :span="24">
                  <el-form-item label="接口名称" prop="apiName">
                     <el-input v-model="form.apiName" placeholder="请输入接口名称，如：股票基本信息" />
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="接口代码" prop="apiCode">
                     <el-input v-model="form.apiCode" placeholder="请输入Tushare接口代码，如：stock_basic" />
                     <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                        示例：stock_basic, daily_basic, trade_cal 等
                     </div>
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="接口描述" prop="apiDesc">
                     <el-input v-model="form.apiDesc" type="textarea" :rows="3" placeholder="请输入接口描述" />
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="接口参数" prop="apiParams">
                     <el-input 
                        v-model="form.apiParams" 
                        type="textarea" 
                        :rows="6" 
                        placeholder='请输入JSON格式的参数，如：{"exchange": "", "list_status": "L"}'
                     />
                     <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                        格式：JSON对象，例如：{"exchange": "", "list_status": "L"}<br/>
                        注意：参数会根据不同接口而不同，请参考Tushare文档
                     </div>
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="数据字段" prop="dataFields">
                     <el-input 
                        v-model="form.dataFields" 
                        type="textarea" 
                        :rows="4" 
                        placeholder='请输入JSON数组格式的字段列表，如：["ts_code", "symbol", "name"]'
                     />
                     <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                        格式：JSON数组，例如：["ts_code", "symbol", "name"]<br/>
                        留空则下载所有字段
                     </div>
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="主键字段" prop="primaryKeyFields">
                     <el-input 
                        v-model="form.primaryKeyFields" 
                        type="textarea" 
                        :rows="3" 
                        placeholder='请输入JSON数组格式的主键字段列表，如：["ts_code", "trade_date"]'
                     />
                     <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                        <div><strong>主键字段说明：</strong></div>
                        <div>• 格式：JSON数组，例如：["ts_code", "trade_date"]（支持复合主键）</div>
                        <div>• 留空则使用默认主键 data_id（自增ID）</div>
                        <div>• 主键字段必须存在于数据字段中</div>
                        <div>• 创建新表时会使用配置的主键字段创建复合主键</div>
                        <div>• 已存在的表会继续使用原有主键，不受此配置影响</div>
                        <div style="margin-top: 5px; color: #E6A23C;">
                           <strong>注意：</strong>如果表已存在，系统会优先使用表实际主键，而不是接口配置的主键字段
                        </div>
                     </div>
                  </el-form-item>
               </el-col>
               <el-col :span="24" v-if="form.configId !== undefined">
                  <el-form-item label="状态">
                     <el-radio-group v-model="form.status">
                        <el-radio
                           v-for="dict in sys_normal_disable"
                           :key="dict.value"
                           :value="dict.value"
                        >{{ dict.label }}</el-radio>
                     </el-radio-group>
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="备注" prop="remark">
                     <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
                  </el-form-item>
               </el-col>
            </el-row>
         </el-form>
         <template #footer>
            <div class="dialog-footer">
               <el-button type="primary" @click="submitForm">确 定</el-button>
               <el-button @click="cancel">取 消</el-button>
            </div>
         </template>
      </el-dialog>
   </div>
</template>

<script setup name="ApiConfig">
import { listApiConfig, getApiConfig, delApiConfig, addApiConfig, updateApiConfig, changeApiConfigStatus, exportApiConfig } from "@/api/tushare/apiConfig"

const { proxy } = getCurrentInstance();
const { sys_normal_disable } = proxy.useDict("sys_normal_disable");

const apiConfigList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    apiName: undefined,
    apiCode: undefined,
    status: undefined
  },
  rules: {
    apiName: [{ required: true, message: "接口名称不能为空", trigger: "blur" }],
    apiCode: [{ required: true, message: "接口代码不能为空", trigger: "blur" }],
    apiParams: [
      {
        validator: (rule, value, callback) => {
          if (value && value.trim()) {
            try {
              JSON.parse(value);
              callback();
            } catch (e) {
              callback(new Error("接口参数必须是有效的JSON格式"));
            }
          } else {
            callback();
          }
        },
        trigger: "blur"
      }
    ],
    dataFields: [
      {
        validator: (rule, value, callback) => {
          if (value && value.trim()) {
            try {
              const parsed = JSON.parse(value);
              if (!Array.isArray(parsed)) {
                callback(new Error("数据字段必须是JSON数组格式"));
              } else {
                callback();
              }
            } catch (e) {
              callback(new Error("数据字段必须是有效的JSON数组格式"));
            }
          } else {
            callback();
          }
        },
        trigger: "blur"
      }
    ],
    primaryKeyFields: [
      {
        validator: (rule, value, callback) => {
          if (value && value.trim()) {
            try {
              const parsed = JSON.parse(value);
              if (!Array.isArray(parsed)) {
                callback(new Error("主键字段必须是JSON数组格式"));
              } else if (parsed.length === 0) {
                callback(new Error("主键字段数组不能为空"));
              } else {
                callback();
              }
            } catch (e) {
              callback(new Error("主键字段必须是有效的JSON数组格式"));
            }
          } else {
            callback();
          }
        },
        trigger: "blur"
      }
    ]
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询接口配置列表 */
function getList() {
  loading.value = true;
  listApiConfig(queryParams.value).then(response => {
    apiConfigList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

/** 取消按钮 */
function cancel() {
  open.value = false;
  reset();
}

/** 表单重置 */
function reset() {
  form.value = {
    configId: undefined,
    apiName: undefined,
    apiCode: undefined,
    apiDesc: undefined,
    apiParams: undefined,
    dataFields: undefined,
    primaryKeyFields: undefined,
    status: "0",
    remark: undefined
  };
  proxy.resetForm("apiConfigRef");
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.configId);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

// 状态修改
function handleStatusChange(row) {
  let text = row.status === "0" ? "启用" : "停用";
  proxy.$modal.confirm('确认要"' + text + '""' + row.apiName + '"接口配置吗?').then(function () {
    return changeApiConfigStatus(row.configId, row.status);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
  }).catch(function () {
    row.status = row.status === "0" ? "1" : "0";
  });
}

/** 新增按钮操作 */
function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加接口配置";
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  const configId = row.configId || ids.value[0];
  if (!configId) {
    proxy.$modal.msgError("请选择要修改的接口配置");
    return;
  }
  getApiConfig(configId).then(response => {
    form.value = response.data;
    // 确保configId被正确设置
    if (!form.value.configId) {
      form.value.configId = configId;
    }
    // 处理主键字段：如果为null或undefined，转换为空字符串，确保在文本框中正确显示
    if (form.value.primaryKeyFields === null || form.value.primaryKeyFields === undefined) {
      form.value.primaryKeyFields = '';
    }
    console.log('修改接口配置，获取到的数据:', form.value);
    open.value = true;
    title.value = "修改接口配置";
  }).catch(error => {
    console.error('获取接口配置详情失败:', error);
    proxy.$modal.msgError("获取接口配置详情失败");
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["apiConfigRef"].validate(valid => {
    if (valid) {
      // 确保主键字段总是被发送，即使是undefined也转换为空字符串
      const submitData = { ...form.value };
      if (submitData.primaryKeyFields === undefined || submitData.primaryKeyFields === null) {
        submitData.primaryKeyFields = '';
      }
      
      // 确保configId被正确传递（修改时必须包含configId）
      const configId = form.value.configId;
      console.log('提交表单，form.value:', form.value);
      console.log('提交表单，configId:', configId, '类型:', typeof configId);
      
      if (configId != undefined && configId != null && configId !== '') {
        // 修改操作：确保configId被包含在提交数据中
        submitData.configId = configId;
        console.log('修改接口配置，configId:', submitData.configId, '提交数据:', JSON.stringify(submitData, null, 2));
        updateApiConfig(submitData).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        }).catch(error => {
          console.error('修改接口配置失败:', error);
          proxy.$modal.msgError("修改失败：" + (error.response?.data?.msg || error.message || '未知错误'));
        });
      } else {
        // 新增操作：确保不包含configId
        delete submitData.configId;
        console.log('新增接口配置，提交数据:', JSON.stringify(submitData, null, 2));
        addApiConfig(submitData).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        }).catch(error => {
          console.error('新增接口配置失败:', error);
          proxy.$modal.msgError("新增失败：" + (error.response?.data?.msg || error.message || '未知错误'));
        });
      }
    }
  });
}

/** 删除按钮操作 */
function handleDelete(row) {
  const configIds = row.configId || ids.value;
  proxy.$modal.confirm('是否确认删除接口配置编号为"' + configIds + '"的数据项?').then(function () {
    return delApiConfig(configIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

/** 导出按钮操作 */
function handleExport() {
  proxy.download("tushare/apiConfig/export", {
    ...queryParams.value,
  }, `apiConfig_${new Date().getTime()}.xlsx`);
}

getList();
</script>
