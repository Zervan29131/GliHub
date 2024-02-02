<template>
<div>
    <Card>
        <div slot="title">
            <div class="edit-head">
                <a @click="close" class="back-title">
                    <Icon type="ios-arrow-back" />返回
                </a>
                <div class="head-name">编辑实验室</div>
                <span></span>
                <a @click="close" class="window-close">
                    <Icon type="ios-close" size="31" class="ivu-icon-ios-close" />
                </a>
            </div>
        </div>
        <Form ref="form" :model="form" :label-width="100" :rules="formValidate" label-position="left">
            <FormItem label="实验室名称" prop="title">
                <Input v-model="form.title" clearable show-word-limit maxlength="240" placeholder="请输入实验室名称..." style="width:570px" />
            </FormItem>
            <FormItem label="地址" prop="address">
                <Input v-model="form.address" clearable show-word-limit maxlength="240" placeholder="请输入实验室地址..." style="width:570px" />
            </FormItem>
            <FormItem label="介绍" prop="about">
                <Input v-model="form.about" clearable show-word-limit maxlength="240" type="textarea" :rows="4" placeholder="请输入实验室介绍..." style="width:570px" />
            </FormItem>
            <FormItem label="负责人" prop="dutyUser">
                <Select v-model="form.dutyUser" clearable placeholder="请选择实验室的负责人..." style="width:570px">
                    <Option v-for="(item,index) in userList" :key="index" :value="item.nickname">{{item.nickname}}</Option>
                </Select>
            </FormItem>
            <FormItem label="类型" prop="type">
                <Select v-model="form.type" clearable placeholder="请选择实验室的类型..." style="width:570px">
                    <Option v-for="(item,index) in typeList" :key="index" :value="item.title">{{item.title}}</Option>
                </Select>
            </FormItem>
            <FormItem label="照片" prop="image">
                <upload-pic-input v-model="form.image" placeholder="选填实验室的照片..." style="width:570px"></upload-pic-input>
            </FormItem>
            <FormItem label="最大人数" prop="number">
                <InputNumber v-model="form.number" min="0" max="5000000" placeholder="请填写实验室的最大容纳人数..." style="width:570px"></InputNumber>
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
    editLaboratory,
    getLaboratoryTypeList,
    getUserList
} from "./api.js";
import uploadPicInput from "@/views/template/upload-pic-input";
export default {
    name: "edit",
    components: {
        uploadPicInput,
    },
    props: {
        data: Object
    },
    data() {
        return {
            submitLoading: false, // 表单提交状态
            form: { // 添加或编辑表单对象初始化数据
                title: "",
                address: "",
                about: "",
                dutyUser: "",
                type: "",
                image: "",
                number: 0,
            },
            // 表单验证规则
            formValidate: {},
            typeList: [],
            userList: []
        };
    },
    methods: {
        init() {
            this.getLaboratoryTypeListFx();
            this.getUserListFx();
            this.handleReset();
            this.form = this.data;
        },
        getLaboratoryTypeListFx() {
            var that = this;
            getLaboratoryTypeList().then(res => {
                if (res.success) {
                    that.typeList = res.result;
                }
            })
        },
        getUserListFx() {
            var that = this;
            getUserList().then(res => {
                if (res.success) {
                    that.userList = res.result;
                }
            })
        },
        handleReset() {
            this.$refs.form.resetFields();
        },
        handleSubmit() {
            this.$refs.form.validate(valid => {
                if (valid) {
                    editLaboratory(this.form).then(res => {
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
