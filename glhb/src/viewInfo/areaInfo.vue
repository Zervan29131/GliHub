<template>
	<div>
		<div class="container">
			<div class="handle-box">
				<el-select v-model="query.address" placeholder="部门" class="handle-select mr10">
					<el-option key="1" label="一部门" value="一部门"></el-option>
					<el-option key="2" label="二部门" value="二部门"></el-option>
				</el-select>
				<el-input v-model="query.name" placeholder="用户名" class="handle-input mr10"></el-input>
				<el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
				<el-button type="primary" :icon="Plus">新增</el-button>
			</div>

			<!-- 用户信息 -->
			<el-table :data="categorys" class="table" style="width: 100%" ref="multipleTable"
				header-cell-class-name="table-header">
				<el-table-column label="ID" width="100" type="index" prop="id"> </el-table-column>
				<el-table-column label="作业区名称" prop="areaName"> </el-table-column>
				<el-table-column label="负责人一" prop="Name1"></el-table-column>
				<el-table-column label="电话" prop="Telephone1"></el-table-column>
				<el-table-column label="负责人二" prop="Name2"></el-table-column>
				<el-table-column label="电话" prop="Telephone2"></el-table-column>
				<el-table-column label="位置" prop="Location"></el-table-column>
				<el-table-column label="备注" prop="Remark"></el-table-column>
				<!-- 数据为空时 -->
				<template #empty>
					<el-empty description="没有数据" />
				</template>
				<!-- 操作 -->
				<el-table-column label="操作" width="220" align="center">
					<template #default="scope">
						<el-button text :icon="Edit" @click="handleEdit(scope.$index, scope.row)" v-permiss="15">
							编辑
						</el-button>
						<el-button text :icon="Delete" class="red" @click="handleDelete(scope.$index)" v-permiss="16">
							删除
						</el-button>
					</template>
				</el-table-column>


			</el-table>


			<div class="pagination">
				<el-pagination background layout="total, prev, pager, next" :current-page="query.pageIndex"
					:page-size="query.pageSize" :total="pageTotal" @current-change="handlePageChange"></el-pagination>
			</div>


		</div>

		<!-- 编辑弹出框 -->
		<el-dialog title="编辑" v-model="editVisible" width="30%">
			<el-form label-width="70px">
				<el-form-item label="用户名">
					<el-input v-model="form.name"></el-input>
				</el-form-item>
				<el-form-item label="地址">
					<el-input v-model="form.address"></el-input>
				</el-form-item>
			</el-form>

			<template #footer>
				<span class="dialog-footer">
					<el-button @click="editVisible = false">取 消</el-button>
					<el-button type="primary" @click="saveEdit">确 定</el-button>
				</span>
			</template>
		</el-dialog>
	</div>
</template>

<script setup lang="ts" name="basetable">

import { ref, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Edit, Search, Plus } from '@element-plus/icons-vue';
import { fetchData } from '../api/index';
// 人员信息引用
const tableData = ref<TableItem[]>([]);
interface TableItem {
	id: number;
	name: string;
	money: string;
	state: string;
	date: string;
	address: string;
}
// 人员信息数据
const categorys = ref([
	{
		"id": 31,
		"areaName": "一号矿区",
		"Name1": "张三",
		"Telephone1": "13512345678",
		"Name2": "王五",
		"Telephone2": "13512345678",
		"Location": "经纬路十号",
		"Remark": "",
	},
	{
		"id": 31,
		"areaName": "二号矿区",
		"Name1": "张三",
		"Telephone1": "13512345678",
		"Name2": "王五",
		"Telephone2": "13512345678",
		"Location": "经纬路十号",
		"Remark": "",
	},
	{
		"id": 31,
		"areaName": "三号矿区",
		"Name1": "张三",
		"Telephone1": "13512345678",
		"Name2": "王五",
		"Telephone2": "13512345678",
		"Location": "经纬路十号",
		"Remark": "",
	},
])

const query = reactive({
	address: '',
	name: '',
	pageIndex: 1,
	pageSize: 10
});


const pageTotal = ref(0);
// 获取表格数据
const getData = () => {
	fetchData().then(res => {
		tableData.value = res.data.list;
		pageTotal.value = res.data.pageTotal || 50;
	});
};
getData();

// 查询操作
const handleSearch = () => {
	query.pageIndex = 1;
	getData();
};
// 分页导航
const handlePageChange = (val: number) => {
	query.pageIndex = val;
	getData();
};

// 删除操作
const handleDelete = (index: number) => {
	// 二次确认删除
	ElMessageBox.confirm('确定要删除吗？', '提示', {
		type: 'warning'
	})
		.then(() => {
			ElMessage.success('删除成功');
			tableData.value.splice(index, 1);
		})
		.catch(() => { });
};

// 表格编辑时弹窗和保存
const editVisible = ref(false);
let form = reactive({
	name: '',
	address: ''
});
let idx: number = -1;
const handleEdit = (index: number, row: any) => {
	idx = index;
	form.name = row.name;
	form.address = row.address;
	editVisible.value = true;
};
const saveEdit = () => {
	editVisible.value = false;
	ElMessage.success(`修改第 ${idx + 1} 行成功`);
	tableData.value[idx].name = form.name;
	tableData.value[idx].address = form.address;
};
</script>

<style scoped>
.handle-box {
	margin-bottom: 20px;
}

.handle-select {
	width: 120px;
}

.handle-input {
	width: 300px;
}

.table {
	width: 100%;
	font-size: 14px;
}

.red {
	color: #F56C6C;
}

.mr10 {
	margin-right: 10px;
}

.table-td-thumb {
	display: block;
	margin: auto;
	width: 40px;
	height: 40px;
}
</style>
