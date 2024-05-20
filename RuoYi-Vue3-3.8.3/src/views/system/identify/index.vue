<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="68px">
      <el-form-item label="风险名称" prop="postCode">
        <el-input v-model="queryParams.postCode" placeholder="请输入风险点名称" clearable @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="风险类型" prop="postName">
        <el-input v-model="queryParams.postName" placeholder="请输入风险类型" clearable @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="风险等级" prop="postName">
        <el-input v-model="queryParams.postName" placeholder="请输入风险等级" clearable @keyup.enter="handleQuery" />
      </el-form-item>
      <!-- <el-form-item label="选择日期" prop="postName">
              <el-input v-model="queryParams.postName" placeholder="请输入选择日期" clearable @keyup.enter="handleQuery" />
          </el-form-item> -->

      <!-- <el-form-item label="状态" prop="status">
              <el-select v-model="queryParams.status" placeholder="设备状态" clearable>
                  <el-option v-for="dict in sys_normal_disable" :key="dict.value" :label="dict.label" :value="dict.value" />
              </el-select>
          </el-form-item> -->
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>



    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd" v-hasPermi="['system:post:add']">新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="success" plain icon="Edit" :disabled="single" @click="handleUpdate"
          v-hasPermi="['system:post:edit']">修改</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete"
          v-hasPermi="['system:post:remove']">删除</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="warning" plain icon="Download" @click="handleExport"
          v-hasPermi="['system:post:export']">导出</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>


    <el-table :data="tableData" style="width: 100%">
      <el-table-column prop="aaa01" align="center" label="任务" width="110" />
      <el-table-column prop="aaa02" align="center" label="工序" width="110" />
      <el-table-column prop="aaa03" align="center" label="危险源" width='110' />
      <el-table-column prop="aaa04" align="center" label="风险类型" width="40" />
      <el-table-column prop="aaa05" align="center" label="风险及后果描述" width="110" />
      <el-table-column prop="aaa06" align="center" label="事故类型" width="60" />

      <el-table-column align="center" label="风险评估">
        <el-table-column prop="bbb01" align="center" label="可能性" width="40" />
        <el-table-column prop="bbb02" align="center" label="损失" width="40" />
        <el-table-column prop="bbb03" align="center" label="风险值" width="40" />
        <el-table-column prop="bbb04" align="center" label="风险等级" width="40" />
      </el-table-column>
      <el-table-column prop="ccc05" align="center" label="管理人员" width="50" />
      <el-table-column prop="ccc06" align="center" label="管理标准" width="200" />
      <el-table-column prop="ccc07" align="center" label="改进措施" width="110" />
      <el-table-column prop="ccc08" align="center" label="监管人员" width="50" />
      <el-table-column prop="ccc09" align="center" label="监管措施" width="70" />
      <el-table-column label="操作" align="center" width="180" class-name="small-padding fixed-width">
                <template #default="scope">
                    <el-button size="mini" type="text" icon="Edit" @click="handleUpdate(scope.row)"
                        v-hasPermi="['system:post:edit']">修改</el-button>
                    <el-button size="mini" type="text" icon="Delete" @click="handleDelete(scope.row)"
                        v-hasPermi="['system:post:remove']">删除</el-button>
                </template>
            </el-table-column>

    </el-table>

    <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize" @pagination="getList" />

    <!-- 添加或修改设备对话框 -->
    <el-dialog :title="title" v-model="open" width="500px" append-to-body>
      <el-form ref="postRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="设备名称" prop="postName">
          <el-input v-model="form.postName" placeholder="请输入设备名称" />
        </el-form-item>
        <!-- <el-form-item label="设备编码" prop="postCode">
                  <el-input v-model="form.postCode" placeholder="请输入编码名称" />
              </el-form-item> -->
        <el-form-item label="设备型号" prop="postCode">
          <el-input v-model="form.postCode" placeholder="请输入设备型号" />
        </el-form-item>
        <el-form-item label="存放地点" prop="postPlace">
          <el-select v-model="form.postPlace" placeholder="请选择存放地点">
            <el-option v-for="(item, index) in postPlacedata" :key="index" :label="item.label" :value="item.value"
              :disabled="item.disabled"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="保管人员" prop="postPerson">
          <el-select v-model="form.postPerson" placeholder="请选择保管人员">
            <el-option v-for="(item, index) in postPersondata" :key="index" :label="item.label" :value="item.value"
              :disabled="item.disabled"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="联系方式" prop="postContact">
          <el-input v-model="form.postContact" placeholder="请输入联系方式" />
        </el-form-item>
        <!-- <el-form-item label="设备状态" prop="status">
                  <el-radio-group v-model="form.status">
                      <el-radio v-for="dict in dict.type.sys_normal_disable" :key="dict.value" :label="dict.value">{{
                          dict.label }}</el-radio>
                  </el-radio-group>
              </el-form-item> -->
        <!-- 
              <el-form-item label="设备顺序" prop="postSort">
                  <el-input-number v-model="form.postSort" controls-position="right" :min="0" />
              </el-form-item> -->

        <el-form-item label="设备状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio v-for="dict in sys_normal_disable" :key="dict.value" :label="dict.value">{{ dict.label
              }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" placeholder="请输入内容" />
        </el-form-item>
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

<script setup name="Post">
import { listPost, addPost, delPost, getPost, updatePost } from "@/api/system/equip";

const { proxy } = getCurrentInstance();
const { sys_normal_disable } = proxy.useDict("sys_normal_disable");

const postList = ref([]);
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
    postCode: undefined,
    postName: undefined,
    status: undefined
  },
  rules: {
    postName: [
      { required: true, message: "设备名称不能为空", trigger: "blur" }
    ],
    postCode: [
      { required: true, message: "设备型号不能为空", trigger: "blur" }
    ],
    // postPerson: [
    //   { required: true, message: "保管人员不能为空", trigger: "blur" }
    // ],
    // postPlace: [
    //   { required: true, message: "存放地点不能为空", trigger: "blur" }
    // ],
  },
  //新增设备数据
  postPlacedata: [{
    "label": "作业区一",
    "value": 1
  }, {
    "label": "作业区二",
    "value": 2
  }],
  postPersondata: [{
    "label": "张三",
    "value": 1
  }, {
    "label": "李四",
    "value": 2
  }],
});

const tableData = [
  {
    aaa01: '安全设备维修',
    aaa02: '检查安全设备',
    aaa03: '未按要求检修',
    aaa04: '人',
    aaa05: '造成设备损坏',
    aaa06: '机电事故',
    bbb01: '3',
    bbb02: '5',
    bbb03: '6',
    bbb04: '黄色',
    ccc05: '张三',
    ccc06: '维修工对其进行详细检查',
    ccc07: '继续整改',
    ccc08: '李四',
    ccc09: '通过',
  },
  {
    aaa01: '配电柜除尘',
    aaa02: '检查瓦斯浓度',
    aaa03: '瓦斯浓度超标',
    aaa04: '环',
    aaa05: '遇明火导致瓦斯事故', 
    aaa06: '瓦斯事故',
    bbb01: '2',
    bbb02: '3',
    bbb03: '8',
    bbb04: '蓝色',
    ccc05: '李某',
    ccc06: '配电柜周围环境瓦斯浓度不能超过0.5%',
    ccc07: '单位定期对矿井维修工进行培训',
    ccc08: '王某',
    ccc09: '通过',
  },
  {
    aaa01: '操作和检查消防器材是否就位',
    aaa02: '检查消防器材等',
    aaa03: '未按要求检查消防器材',
    aaa04: '人',
    aaa05: '发生火灾',
    aaa06: '火灾事故',
    bbb01: '2',
    bbb02: '6',
    bbb03: '5',
    bbb04: '蓝色',
    ccc05: '张某',
    ccc06: '必须检查确认消防管路通畅，消防栓齐全，发现问题通知班长立即处理。',
    ccc07: '发现消防器材失效、缺失时给予安全管理人员处理。',
    ccc08: '刘某',
    ccc09: '通过',
  },
 
]

const { queryParams, form, rules } = toRefs(data);

/** 查询设备列表 */
function getList() {
  loading.value = true;
  listPost(queryParams.value).then(response => {
    postList.value = response.rows;
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
    postId: undefined,
    postCode: undefined,
    postName: undefined,
    postSort: 0,
    status: "0",
    remark: undefined
  };
  proxy.resetForm("postRef");
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
/** 多选框选中数据 */
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.postId);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}
/** 新增按钮操作 */
function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加设备";
}
/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  const postId = row.postId || ids.value;
  getPost(postId).then(response => {
    form.value = response.data;
    open.value = true;
    title.value = "修改设备";
  });
}
/** 提交按钮 */
function submitForm() {
  proxy.$refs["postRef"].validate(valid => {
    if (valid) {
      if (form.value.postId != undefined) {
        updatePost(form.value).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addPost(form.value).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}
/** 删除按钮操作 */
function handleDelete(row) {
  const postIds = row.postId || ids.value;
  proxy.$modal.confirm('是否确认删除设备编号为"' + postIds + '"的数据项？').then(function () {
    return delPost(postIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => { });
}
/** 导出按钮操作 */
function handleExport() {
  proxy.download("system/post/export", {
    ...queryParams.value
  }, `post_${new Date().getTime()}.xlsx`);
}

getList();




</script>