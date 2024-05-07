<template>
	<el-table :data="categorys1" class="table" style="width: 100%" ref="multipleTable"
		:header-cell-style="{ 'text-align': 'center' }" header-cell-class-name="table-header">

		<template #header>
			<el-input v-model="search" size="small" placeholder="Type to search" />
		</template>

		<el-table-column label="ID" width="100" type="index" prop="id" align="center"> </el-table-column>
		<el-table-column label="主要危险源" width="200" prop="Type" align="center"> </el-table-column>
		<el-table-column label="危险源相关信息" width="600" prop="Name" align="center"></el-table-column>
		<el-table-column label="危险性" prop="Remark" align="center"></el-table-column>

		<el-table-column align="center" label="操作" width="300">
	        <template #default="scope">
               <el-button type="text" icon="Edit" @click="handleUpdate(scope.row)"
                  v-hasPermi="['system:notice:edit']">详情</el-button>
               <el-button type="text" icon="Delete" @click="handleDelete(scope.row)" color="red"
                  v-hasPermi="['system:notice:remove']">删除</el-button>
            </template>
		</el-table-column>


	</el-table>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'

interface User {
	date: string
	name: string
	address: string
}

const search = ref('')
const filterTableData = computed(() =>
	tableData.filter(
		(data) =>
			!search.value ||
			data.name.toLowerCase().includes(search.value.toLowerCase())
	)
)
const handleEdit = (index: number, row: User) => {
	console.log(index, row)
}
const handleDelete = (index: number, row: User) => {
	console.log(index, row)
}

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
	}
])
const categorys1 = ref([
	{
		"id": 31,
		"Name": "来源于一号作业区",
		"Type": "一氧化碳",
		"Remark": "是一种易燃易爆气体",
	},
	{
		"id": 31,
		"Name": "一号作业区与二号作业区的气体运输管道",
		"Type": "压力容器与压力管道",
		"Remark": "破损会产生剧烈爆炸",
	},

])

const tableData: User[] = [
	{
		date: '2016-05-03',
		name: 'Tom',
		address: 'No. 189, Grove St, Los Angeles',
	},
	{
		date: '2016-05-02',
		name: 'John',
		address: 'No. 189, Grove St, Los Angeles',
	},
	{
		date: '2016-05-04',
		name: 'Morgan',
		address: 'No. 189, Grove St, Los Angeles',
	},
	{
		date: '2016-05-01',
		name: 'Jessy',
		address: 'No. 189, Grove St, Los Angeles',
	},
]
</script>
