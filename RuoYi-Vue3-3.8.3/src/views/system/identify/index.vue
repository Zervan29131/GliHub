<template>

	<div class="app-container">

		<!-- 用户信息 -->
		<el-table :data="categorys" class="table" style="width: 100%" ref="multipleTable"  :header-cell-style="{'text-align':'center'}"
			header-cell-class-name="table-header">
			<el-table-column label="ID" width="100" type="index" prop="id"  align="center"> </el-table-column>
			<el-table-column label="事故类型" width="220" prop="Type"  align="center"> </el-table-column>
			<el-table-column label="事故方案" width="300" prop="Name"  align="center"></el-table-column>
			<el-table-column label="备注" prop="Remark"  align="center"></el-table-column>
			<!-- 数据为空时 -->
			<template #empty>
				<el-empty description="没有数据" />
			</template>

			<!-- 操作 -->
			<el-table-column label="操作" width="400" align="center">
				<template #default="scope">
					<!-- <el-button text :icon="Edit" @click="handleEdit(scope.$index, scope.row)" v-permiss="15">
						编辑
					</el-button> -->
					<el-button text :icon="Edit" plain @click="dialogVisible = true" v-permiss="15">
						详细内容
					</el-button>
					<el-button text :icon="Delete" class="red" @click="handleDelete(scope.$index)" v-permiss="16">
						删除
					</el-button>
				</template>
			</el-table-column>
		</el-table>

		<!-- <el-dialog v-model="dialogVisible" title="压力容器与压力管道事故现场处置方案" width="500" :before-close="handleClose"> 弹出窗口关闭提示框-->
		<el-dialog v-model="dialogVisible" title="压力容器与压力管道事故现场处置方案" width="500">
			<span> <el-table :data="tableData2" border style="width: 100%"   :header-cell-style="{'text-align':'center'}">
					<el-table-column prop="date" label="压力容器与压力管道事故现场处置方案"  >


						<el-table-column label="事故特征" slot-scope="scope">
							<el-table-column prop="state" label="事故类型和危险程度" align="center" />
							<el-table-column prop="city" label="事故征兆" align="center" />
							<el-table-column prop="address" label="事故发生区域" align="center"/>
						</el-table-column>


						<el-table-column label="应急组织与职责">
							<el-table-column prop="state" label="应急小组"  align="center"/>
							<el-table-column prop="city" label="应急小组职责"  align="center"/>
							<el-table-column prop="address" label="应急小组成员职责" align="center"/>
						</el-table-column>

						<el-table-column prop="name" label="危险后果"  />

					</el-table-column>
				</el-table></span>

			<template #footer>
				<div class="dialog-footer">
					<el-button type="primary" @click="dialogVisible = false">
						编辑表格
					</el-button>
					<el-button @click="dialogVisible = false">删除表格</el-button>
				</div>
			</template>
		</el-dialog>
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Edit, Search, Plus } from '@element-plus/icons-vue';
// import { fetchData } from '../api/index';

const dialogVisible = ref(false)

// const handleClose = (done: () => void) => {
// 	ElMessageBox.confirm('你确定取消编辑吗？')
// 		.then(() => {
// 			done()
// 		})
// 		.catch(() => {
// 			// catch error
// 		})
// }
const tableData2 = [
	{
		date: '2016-05-03',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-02',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-04',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-01',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-08',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-06',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
	{
		date: '2016-05-07',
		name: 'Tom',
		state: 'California',
		city: 'Los Angeles',
		address: 'No. 189, Grove St, Los Angeles',
		zip: 'CA 90036',
	},
]
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
// 事故类型信息数据
const categorys = ref([
	{
		"id": 31,
		"Name": "压力容器与压力管道事故现场处置方案",
		"Type": "化学事故",
		"Remark": "",
	},
	{
		"id": 31,
		"Name": "触电事故发生现场处置方案",
		"Type": "触电事故",
		"Remark": "",
	}, {
		"id": 31,
		"Name": "道具事故现场处置方案",
		"Type": "道具事故",
		"Remark": "",
	},
])

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


</script>

<style scoped>
.transform{
	transform:rotate(90deg);
}
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
