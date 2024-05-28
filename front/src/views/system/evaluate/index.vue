<template>
	<div class="app-container">

		<!--  标签页 -->
		<el-tabs v-model="activeName" type="card" class="demo-tabs" @tab-click="handleClick">

			<!-- 表单 道氏指数法 -->
			<el-tab-pane label="道氏指数法">
				<el-form :model="form" label-width="200px" class="short-input">
					<el-form-item label="工艺单元">
						<el-input v-model="formInline.value1" placeholder="甲醇单元" clearable />
					</el-form-item>
					<el-form-item label="MF物质系数">
						<el-input v-model="formInline.value2" placeholder="16" clearable />
					</el-form-item>
					<el-form-item label="F1一般工艺危险系数">
						<el-input v-model="formInline.value3" placeholder="2" clearable />
					</el-form-item>
					<el-form-item label="F2特殊工艺危险系数">
						<el-input v-model="formInline.value4" placeholder="1.9" clearable />
					</el-form-item>
					<el-form-item label="F3单元危险系数">
						<el-input v-model="formInline.value5" placeholder="3.8" clearable />
					</el-form-item>
					<el-form-item label="F&EI火灾爆炸指数">
						<el-input v-model="formInline.value6" placeholder="60.8" clearable />
					</el-form-item>
					<el-form-item>
						<el-button type="primary" @click="onSubmit">计算</el-button>
						<el-button>重置</el-button>
					</el-form-item>
				</el-form>
			</el-tab-pane>


			<!-- 作业条件危险性分析法 -->
			<el-tab-pane label="作业条件危险性分析法LEC">
				<el-form :model="form" label-width="300px" class="short-input">
					<el-form-item label="事故发生的可能性（L）">
						<el-input v-model="formInline.value1" placeholder="likelihood" clearable />
					</el-form-item>
					<el-form-item label="人员暴露于危险环境中的频繁程度（E）">
						<el-input v-model="formInline.value2" placeholder="exposure" clearable />
					</el-form-item>
					<el-form-item label="一旦发生事故可能造成的后果（C）">
						<el-input v-model="formInline.value3" placeholder="consequence" clearable />
					</el-form-item>
					<el-form-item>
						<el-button type="primary" @click="onSubmit">计算</el-button>
						<el-button>重置</el-button>
					</el-form-item>
				</el-form>
			</el-tab-pane>

	
			<!-- 安全检查表法 -->
			<el-tab-pane label="安全检查表法">
				<el-table :data="tableData" style="width: 100%">
					<el-table-column prop="id" label="序号" width="60" align="center" />
					<el-table-column prop="name" label="检查项目" header-align="center" width="500">
						<template #default="{ row }">
							<div class="center">{{ row.name }}</div>
						</template>
					</el-table-column>
					<el-table-column prop="standard" label="国家技术标准规定项" align="center" width="250" />
					<el-table-column prop="result" label="检查结果" header-align="center" width="120" />
					<el-table-column prop="remark" label="备注" header-align="center" />
					<el-table-column fixed="right" label="选项" width="70">

						<template #default="scope">
							<el-button link type="primary" size="small" @click.prevent="deleteRow(scope.$index)">
								删除
							</el-button>
						</template>
					</el-table-column>
				</el-table>
				<el-button class="mt-4" style="width: 30%" type="primary">生成检查表</el-button>
				<el-button class="mt-4" style="width: 30%" type="primary" @click="onAddItem">添加检查项目</el-button>
				<el-button class="mt-4" style="width: 30%" type="primary" @click="onAddItem">导出该表</el-button>
			</el-tab-pane>

					<!-- 事故模拟分析法 -->
					<el-tab-pane label="爆炸指数危险评价法">爆炸指数危险评价法</el-tab-pane>

		</el-tabs>
	</div>
</template>


<script lang="ts" setup>
// 标签页
import { ref } from 'vue'
import type { TabsPaneContext } from 'element-plus'

const activeName = ref('first')
const handleClick = (tab: TabsPaneContext, event: Event) => {
	console.log(tab, event)
}

// 道氏指数法
import { reactive } from 'vue'
const formInline = reactive({
	value1: '',
	value2: '',
	value3: '',
	value4: '',
	value5: '',
	value6: '',
})
const onSubmit = () => {
	console.log('submit!')
}


//作业条件危险性分析法
import type { FormInstance, FormRules } from 'element-plus'

const ruleFormRef = ref<FormInstance>()

const checkAge = (rule: any, value: any, callback: any) => {
	if (!value) {
		return callback(new Error('Please input the age'))
	}
	setTimeout(() => {
		if (!Number.isInteger(value)) {
			callback(new Error('Please input digits'))
		} else {
			if (value < 18) {
				callback(new Error('Age must be greater than 18'))
			} else {
				callback()
			}
		}
	}, 1000)
}

const validatePass = (rule: any, value: any, callback: any) => {
	if (value === '') {
		callback(new Error('Please input the password'))
	} else {
		if (ruleForm.checkPass !== '') {
			if (!ruleFormRef.value) return
			ruleFormRef.value.validateField('checkPass', () => null)
		}
		callback()
	}
}
const validatePass2 = (rule: any, value: any, callback: any) => {
	if (value === '') {
		callback(new Error('Please input the password again'))
	} else if (value !== ruleForm.pass) {
		callback(new Error("Two inputs don't match!"))
	} else {
		callback()
	}
}

const ruleForm = reactive({
	pass: '',
	checkPass: '',
	age: '',
})

const rules = reactive<FormRules<typeof ruleForm>>({
	pass: [{ validator: validatePass, trigger: 'blur' }],
	checkPass: [{ validator: validatePass2, trigger: 'blur' }],
	age: [{ validator: checkAge, trigger: 'blur' }],
})

const submitForm = (formEl: FormInstance | undefined) => {
	if (!formEl) return
	formEl.validate((valid) => {
		if (valid) {
			console.log('submit!')
		} else {
			console.log('error submit!')
			return false
		}
	})
}

const resetForm = (formEl: FormInstance | undefined) => {
	if (!formEl) return
	formEl.resetFields()
}

//事故模拟分析法

//安全检查表法

import dayjs from 'dayjs'

const now = new Date()

const tableData = ref([

	{
		id: '01',
		name: '  矿山、建筑施工单位和危险物品的生产、经营、储存单位，应当设置安全生产管理机构或者配备专职安全生产管理人员。',
		standard: '《安全生产法》第19条',
		result: ' ',
		remark: ' ',
	},
	{
		id: '02',
		name: '  危险物品的生产、经营、储存单位以及矿山、建筑施工单位的主要负责人和安全生产管理人员，应当由有关主管部门对其安全生产知识和管理能力考核合格后方可任职。考核不得收费。',
		standard: '《安全生产法》第20条',
		result: ' ',
		remark: ' ',
	},
	{
		id: '03',
		name: '  生产经营单位应当对从业人员进行安全生产教育和培训，保证从业人员具备必要的安全生产知识，熟悉有关的安全生产规章制度和安全操作规程，掌握本岗位的安全操作技能。未经安全生产教育和培训合格的从业人员，不得上岗作业。',
		standard: '《安全生产法》第21条',
		result: ' ',
		remark: ' ',
	},
	{
		id: '04',
		name: '生产经营单位进行爆破、吊装等危险作业，应当安排专门人员进行现场安全管理，确保操作规程的遵守和安全措施的落实',
		standard: '《安全生产法》第35条',
		result: ' ',
		remark: ' ',
	},
])

const deleteRow = (index: number) => {
	tableData.value.splice(index, 1)
}

const onAddItem = () => {
	now.setDate(now.getDate() + 1)
	tableData.value.push({
		id: '04',
		name: '生产经营单位进行爆破、吊装等危险作业，应当安排专门人员进行现场安全管理，确保操作规程的遵守和安全措施的落实',
		standard: '《安全生产法》第35条',
		result: ' ',
		remark: ' ',
	})
}
</script>

<style>
/* 标签页 */
.demo-tabs>.el-tabs__content {
	padding: 32px;
	color: #6b778c;
	font-size: 32px;
	font-weight: 600;
}

/* 输入框长度 */
.short-input {
	width: 800px;
}

.center {
	text-indent: 2em;
	/* 根据需要调整缩进大小 */
}

.indented-text {
	text-indent: 20px;
	/* 根据需要调整缩进大小 */
}
</style>