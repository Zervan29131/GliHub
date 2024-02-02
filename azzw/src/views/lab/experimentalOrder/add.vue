<template>
<div>
    <Card>
        <div slot="title">
            <div class="edit-head">
                <a @click="close" class="back-title">
                    <Icon type="ios-arrow-back" />返回
                </a>
                <div class="head-name">添加</div>
                <span></span>
                <a @click="close" class="window-close">
                    <Icon type="ios-close" size="31" class="ivu-icon-ios-close" />
                </a>
            </div>
        </div>
        <Form ref="form" :model="form" :label-width="100" :rules="formValidate" label-position="left">
            <FormItem label="下单人ID" prop="userId">
                <Select v-model="form.userId" clearable style="width:570px">
                    <Option value="0">请自行编辑下拉菜单</Option>
                </Select>
            </FormItem>
            <FormItem label="下单人姓名" prop="userName">
                <Input v-model="form.userName" clearable style="width:570px" />
            </FormItem>
            <FormItem label="手机号" prop="userMobile">
                <Input v-model="form.userMobile" clearable style="width:570px" />
            </FormItem>
            <FormItem label="实验室ID" prop="laboratoryId">
                <Select v-model="form.laboratoryId" clearable style="width:570px">
                    <Option value="0">请自行编辑下拉菜单</Option>
                </Select>
            </FormItem>
            <FormItem label="实验室名称" prop="laboratoryName">
                <Input v-model="form.laboratoryName" clearable style="width:570px" />
            </FormItem>
            <FormItem label="实验ID" prop="experimentId">
                <Select v-model="form.experimentId" clearable style="width:570px">
                    <Option value="0">请自行编辑下拉菜单</Option>
                </Select>
            </FormItem>
            <FormItem label="实验名称" prop="experimentName">
                <Input v-model="form.experimentName" clearable style="width:570px" />
            </FormItem>
            <FormItem label="日期" prop="date">
                <DatePicker type="date" v-model="form.date" clearable style="width:570px"></DatePicker>
            </FormItem>
            <FormItem label="时段" prop="step">
                <Select v-model="form.step" clearable style="width:570px">
                    <Option value="0">请自行编辑下拉菜单</Option>
                </Select>
            </FormItem>
            <FormItem label="顺序号" prop="number">
                <Input v-model="form.number" clearable style="width:570px" />
            </FormItem>
            <FormItem label="是否预定" prop="orderFlag">
                <Input v-model="form.orderFlag" clearable style="width:570px" />
            </FormItem>
            <FormItem label="预定时间" prop="orderTime">
                <Input v-model="form.orderTime" clearable style="width:570px" />
            </FormItem>
            <Form-item class="br">
                <Button @click="handleSubmit" :loading="submitLoading" type="primary">提交并保存</Button>
                <Button @click="handleReset">重置</Button>
                <Button type="dashed" @click="close">关闭</Button>
            </Form-item>
        </Form>
    </Card>
</div>
</template>

<script>
import {
    addExperimentalOrder
} from "./api.js";
export default {
    name: "add",
    components: {},
    data() {
        return {
            submitLoading: false, // 表单提交状态
            form: { // 添加或编辑表单对象初始化数据
                userId: "",
                userName: "",
                userMobile: "",
                laboratoryId: "",
                laboratoryName: "",
                experimentId: "",
                experimentName: "",
                date: "",
                step: "",
                number: "",
                orderFlag: "",
                orderTime: "",
            },
            // 表单验证规则
            formValidate: {}
        };
    },
    methods: {
        init() {},
        handleReset() {
            this.$refs.form.resetFields();
        },
        handleSubmit() {
            this.$refs.form.validate(valid => {
                if (valid) {
                    addExperimentalOrder(this.form).then(res => {
                        this.submitLoading = false;
                        if (res.success) {
                            this.$Message.success("操作成功");
                            this.submited();
                        }
                    });
                }
            });
        },
        close() {
            this.$emit("close", true);
        },
        submited() {
            this.$emit("submited", true);
        }
    },
    mounted() {
        this.init();
    }
};
</script>

<style lang="less">
// 建议引入通用样式 具体路径自行修改 可删除下面样式代码
// @import "../../../styles/single-common.less";
.edit-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;

    .back-title {
        color: #515a6e;
        display: flex;
        align-items: center;
    }

    .head-name {
        display: inline-block;
        height: 20px;
        line-height: 20px;
        font-size: 16px;
        color: #17233d;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .window-close {
        z-index: 1;
        font-size: 12px;
        position: absolute;
        right: 0px;
        top: -5px;
        overflow: hidden;
        cursor: pointer;

        .ivu-icon-ios-close {
            color: #999;
            transition: color .2s ease;
        }
    }

    .window-close .ivu-icon-ios-close:hover {
        color: #444;
    }
}
</style>
