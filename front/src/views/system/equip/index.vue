<template>
    <div class="app-container">
        <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="68px">
            <el-form-item label="设备编码" prop="postCode">
                <el-input v-model="queryParams.postCode" placeholder="请输入设备编码" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="设备名称" prop="postName">
                <el-input v-model="queryParams.postName" placeholder="请输入设备名称" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="状态" prop="status">
                <el-select v-model="queryParams.status" placeholder="设备状态" clearable>
                    <el-option v-for="dict in sys_normal_disable" :key="dict.value" :label="dict.label" :value="dict.value" />
                </el-select>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
                <el-button icon="Refresh" @click="resetQuery">重置</el-button>
            </el-form-item>
        </el-form>



        <el-row :gutter="10" class="mb8">
            <el-col :span="1.5">
                <el-button type="primary" plain icon="Plus" @click="handleAdd"
                    v-hasPermi="['system:post:add']">新增</el-button>
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


        <el-table v-loading="loading" :data="postList" @selection-change="handleSelectionChange">
            <el-table-column type="selection" width="55" align="center" />
            <el-table-column label="设备编号" align="center" prop="postId" />
            <el-table-column label="设备名称" align="center" prop="postName" width="300"/>

            <!-- <el-table-column label="岗位排序" align="center" prop="postSort" /> -->

            <el-table-column label="设备型号" align="center" prop="postCode"  />
            <el-table-column label="存放地点" align="center" prop="postPlace" width="100"/>
            <el-table-column label="保管人员" align="center" prop="postPerson" width="100"/>
            <el-table-column label="联系方式" align="center" prop="postContect" width="100"/>
            <el-table-column label="运行使用情况" align="center" prop="status">
                <template #default="scope">
                    <dict-tag :options="sys_normal_disable" :value="scope.row.status" />

                    <!-- <dict-tag :options="dict.type.sys_normal_disable" :value="scope.row.status" /> -->
                </template>
            </el-table-column>
            <el-table-column label="创建时间" align="center" prop="createTime" width="180">
                <template #default="scope">
                    <span>{{ parseTime(scope.row.createTime) }}</span>
                </template>
            </el-table-column>
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
                        <el-option v-for="(item, index) in postPlacedata" :key="index" :label="item.label"
                            :value="item.value" :disabled="item.disabled"></el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="保管人员" prop="postPerson">
                    <el-select v-model="form.postPerson" placeholder="请选择保管人员">
                        <el-option v-for="(item, index) in postPersondata" :key="index" :label="item.label"
                            :value="item.value" :disabled="item.disabled"></el-option>
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