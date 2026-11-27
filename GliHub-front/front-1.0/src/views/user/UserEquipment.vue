<script setup>
import {
    Edit,
    Delete
} from '@element-plus/icons-vue'
import { ref } from 'vue'
const categorys = ref([
    {
        "id": 31,
        "Name": "设备一",
        "Telephone": "13512345678",
        "Department": "一部门",
        "authority": "管理员",
        "createTime": "2023-09-02 12:06:59",
        "updateTime": "2023-09-02 12:06:59"
    },
    {
        "id": 4,
        "Name": "设备二",
        "Telephone": "13512345678",
        "Department": "一部门",
        "authority": "普通用户",
        "createTime": "2023-09-02 12:08:16",
        "updateTime": "2023-09-02 12:08:16"
    },
    {
        "id": 5,
        "Name": "设备三",
        "Telephone": "13512345678",
        "Department": "一部门",
        "authority": "普通用户",
        "createTime": "2023-09-02 12:08:33",
        "updateTime": "2023-09-02 12:08:33"
    }
])
</script>
<template>
    <el-card class="page-container">
        <template #header>
            <div class="header">
                <span>人员分类</span>
                <div class="extra">
                    <el-button type="primary">添加分类</el-button>
                </div>
            </div>
        </template>
        <el-table :data="categorys" style="width: 100%">
            <el-table-column label="账号" width="100" type="index" prop="id"> </el-table-column>
            <el-table-column label="姓名"  prop="Name"> </el-table-column>
            <el-table-column label="电话" prop="Telephone"></el-table-column>
            <el-table-column label="部门" prop="Department"></el-table-column>
            <el-table-column label="权限范围" prop="authority"></el-table-column>
            <el-table-column label="操作" width="100">
                <template #default="{ row }">
                    <el-button :icon="Edit" circle plain type="primary" ></el-button>
                    <el-button :icon="Delete" circle plain type="danger"></el-button>
                </template>
            </el-table-column>
            <template #empty>
                <el-empty description="没有数据" />
            </template>
        </el-table>
    </el-card>
</template>

<style lang="scss" scoped>
.page-container {
    min-height: 100%;
    box-sizing: border-box;

    .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
}
</style>