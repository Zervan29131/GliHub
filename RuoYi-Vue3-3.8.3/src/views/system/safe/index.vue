<template>
    <div class="app-container">
        <el-table :data="tableData" style="width: 100%">
            <el-table-column prop="aaa01" align="center" label="序号" width="50" />
            <el-table-column prop="aaa02" align="center" label="应急措施" width="120" />
            <el-table-column prop="aaa03" align="center" label="措施类型" width='100' />
            <el-table-column prop="aaa04" align="center" label="适用场景" width="100" />
            <el-table-column prop="aaa05" align="center" label="执行人员" width="120" />
            <el-table-column prop="aaa06" align="center" label="执行步骤" width="250" />
            <el-table-column prop="aaa07" align="center" label="注意事项" width="200" />
            <el-table-column prop="aaa08" align="center" label="联系方式" width="150" />

            <el-table-column label="操作" align="center" width="180" class-name="small-padding fixed-width">
                <template #default="scope">
                    <el-button size="mini" type="text" icon="Edit" @click="handleUpdate(scope.row)"
                        v-hasPermi="['system:post:edit']">修改</el-button>
                    <el-button size="mini" type="text" icon="Delete" @click="handleDelete(scope.row)"
                        v-hasPermi="['system:post:remove']">删除</el-button>
                </template>
            </el-table-column>

        </el-table>
        <el-button class="mt-4" style="width: 30%" type="primary">添加应急措施</el-button>
        <el-button class="mt-4" style="width: 30%" type="primary">生成应急预案</el-button>
        <el-button class="mt-4" style="width: 30%" type="primary">导出应急预案表</el-button>
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
        aaa01: '01',
        aaa02: '火灾紧急疏散',
        aaa03: '救援措施',
        aaa04: '办公楼发生火灾',
        aaa05: '安全员李某',
        aaa06: '1. 启动警报系统2. 指引员工沿疏散路线撤离3. 清点人数，确保无人遗漏',
        aaa07: '警报系统、疏散路线图',
        aaa08: '13888888888',
    },
    {
        aaa01: '02',
        aaa02: '化学品泄漏应急处理',
        aaa03: '救援与恢复措施',
        aaa04: '化学品泄漏',
        aaa05: '安全员张某',
        aaa06: '1. 立即疏散人员2. 使用专用工具清理泄漏物3. 监测环境，确保安全',
        aaa07: '泄漏处理工具、防护装备',
        aaa08: '13888888888',
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