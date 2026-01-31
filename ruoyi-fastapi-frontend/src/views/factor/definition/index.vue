<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="因子代码" prop="factorCode">
        <el-input
          v-model="queryParams.factorCode"
          placeholder="请输入因子代码"
          clearable
          style="width: 200px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="因子名称" prop="factorName">
        <el-input
          v-model="queryParams.factorName"
          placeholder="请输入因子名称"
          clearable
          style="width: 200px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="类别" prop="category">
        <el-input
          v-model="queryParams.category"
          placeholder="如：技术面/财务面"
          clearable
          style="width: 200px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="启用状态" prop="enableFlag">
        <el-select v-model="queryParams.enableFlag" placeholder="请选择状态" clearable style="width: 200px">
          <el-option label="启用" value="0" />
          <el-option label="停用" value="1" />
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
          v-hasPermi="['factor:definition:add']"
        >新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="success"
          plain
          icon="Edit"
          :disabled="single"
          @click="handleUpdate"
          v-hasPermi="['factor:definition:edit']"
        >修改</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          plain
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['factor:definition:remove']"
        >删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="definitionList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="ID" width="80" align="center" prop="id" />
      <el-table-column label="因子代码" align="center" prop="factorCode" :show-overflow-tooltip="true" />
      <el-table-column label="因子名称" align="center" prop="factorName" :show-overflow-tooltip="true" />
      <el-table-column label="类别" align="center" prop="category" width="120" />
      <el-table-column label="频率" align="center" prop="freq" width="80" />
      <el-table-column label="窗口" align="center" prop="window" width="80" />
      <el-table-column label="计算类型" align="center" prop="calcType" width="120" />
      <el-table-column label="数据来源表" align="center" prop="sourceTable" width="140" :show-overflow-tooltip="true" />
      <el-table-column label="启用状态" align="center" prop="enableFlag" width="100">
        <template #default="scope">
          <el-switch
            v-model="scope.row.enableFlag"
            active-value="0"
            inactive-value="1"
            @change="handleStatusChange(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="备注" align="center" prop="remark" :show-overflow-tooltip="true" />
      <el-table-column label="操作" align="center" width="200" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="修改" placement="top">
            <el-button
              link
              type="primary"
              icon="Edit"
              @click="handleUpdate(scope.row)"
              v-hasPermi="['factor:definition:edit']"
            />
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button
              link
              type="primary"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['factor:definition:remove']"
            />
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

    <!-- 添加或修改因子定义对话框 -->
    <el-dialog :title="title" v-model="open" width="900px" append-to-body>
      <el-form ref="definitionRef" :model="form" :rules="rules" label-width="120px">
        <el-row>
          <el-col :span="24">
            <el-form-item label="因子代码" prop="factorCode">
              <el-input v-model="form.factorCode" placeholder="请输入因子代码，如：MA_5" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="因子名称" prop="factorName">
              <el-input v-model="form.factorName" placeholder="请输入因子名称，如：5日均线" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="因子类别" prop="category">
              <el-input v-model="form.category" placeholder="如：技术面/财务面/情绪面" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="频率" prop="freq">
              <el-select v-model="form.freq" placeholder="请选择频率" style="width: 100%">
                <el-option label="日频(D)" value="D" />
                <el-option label="周频(W)" value="W" />
                <el-option label="月频(M)" value="M" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="窗口长度" prop="window">
              <el-input-number v-model="form.window" :min="1" :step="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计算类型" prop="calcType">
              <el-select v-model="form.calcType" placeholder="请选择计算类型" style="width: 100%">
                <el-option label="Python表达式" value="PY_EXPR" />
                <el-option label="SQL表达式" value="SQL_EXPR" />
                <el-option label="自定义Python函数" value="CUSTOM_PY" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据来源表" prop="sourceTable">
              <el-input v-model="form.sourceTable" placeholder="如：daily_price 或 tushare_xxx" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="计算表达式/函数" prop="expr">
              <el-input
                v-model="form.expr"
                type="textarea"
                :rows="4"
                placeholder='PY_EXPR 示例：(close / close.shift(1) - 1).rolling(window=20).mean()
CUSTOM_PY 示例：module_factor.builtin_factors.momentum_20'
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="依赖因子(JSON)" prop="dependencies">
              <el-input
                v-model="form.dependencies"
                type="textarea"
                :rows="3"
                placeholder='如：["RET_1D", "VOL_5D"]'
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="附加参数(JSON)" prop="params">
              <el-input
                v-model="form.params"
                type="textarea"
                :rows="3"
                placeholder='如：{"min_periods": 3}'
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="启用状态" prop="enableFlag">
              <el-radio-group v-model="form.enableFlag">
                <el-radio value="0">启用</el-radio>
                <el-radio value="1">停用</el-radio>
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

<script setup name="FactorDefinition">
import { listFactorDefinition, addFactorDefinition, updateFactorDefinition, delFactorDefinition } from "@/api/factor/definition"

const { proxy } = getCurrentInstance();

const definitionList = ref([]);
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
    factorCode: undefined,
    factorName: undefined,
    category: undefined,
    enableFlag: undefined
  },
  rules: {
    factorCode: [{ required: true, message: "因子代码不能为空", trigger: "blur" }],
    factorName: [{ required: true, message: "因子名称不能为空", trigger: "blur" }]
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询因子定义列表 */
function getList() {
  loading.value = true;
  listFactorDefinition(queryParams.value).then(response => {
    definitionList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
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
  ids.value = selection.map(item => item.id);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
}

/** 新增按钮操作 */
function handleAdd() {
  resetForm();
  title.value = "新增因子定义";
  open.value = true;
}

/** 修改按钮操作 */
function handleUpdate(row) {
  resetForm();
  form.value = { ...row };
  title.value = "编辑因子定义";
  open.value = true;
}

/** 删除按钮操作 */
function handleDelete(row) {
  const factorIds = row.id || ids.value.join(",");
  proxy.$modal.confirm('是否确认删除因子定义编号为"' + factorIds + '"的数据项？').then(function () {
    return delFactorDefinition(factorIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

/** 状态开关切换 */
function handleStatusChange(row) {
  const text = row.enableFlag === '0' ? "启用" : "停用";
  proxy.$modal.confirm('确认要"' + text + '"因子 "' + row.factorName + '" 吗？').then(function () {
    return updateFactorDefinition(row);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
    getList();
  }).catch(() => {
    // 还原
    row.enableFlag = row.enableFlag === '0' ? '1' : '0';
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["definitionRef"].validate(valid => {
    if (!valid) {
      return;
    }
    if (form.value.id) {
      updateFactorDefinition(form.value).then(() => {
        proxy.$modal.msgSuccess("修改成功");
        open.value = false;
        getList();
      });
    } else {
      addFactorDefinition(form.value).then(() => {
        proxy.$modal.msgSuccess("新增成功");
        open.value = false;
        getList();
      });
    }
  });
}

/** 取消按钮 */
function cancel() {
  open.value = false;
}

/** 表单重置 */
function resetForm() {
  form.value = {
    id: undefined,
    factorCode: undefined,
    factorName: undefined,
    category: undefined,
    freq: 'D',
    window: undefined,
    calcType: 'PY_EXPR',
    expr: undefined,
    sourceTable: undefined,
    dependencies: undefined,
    params: undefined,
    enableFlag: '0',
    remark: undefined
  };
  proxy.resetForm("definitionRef");
}

onMounted(() => {
  getList();
});
</script>

