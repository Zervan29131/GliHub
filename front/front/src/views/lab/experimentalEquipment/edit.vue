<template>
<div>
    <Card>
        <div slot="title">
            <div class="edit-head">
                <a @click="close" class="back-title">
                    <Icon type="ios-arrow-back" />返回
                </a>
                <div class="head-name">编辑实验设备</div>
                <span></span>
                <a @click="close" class="window-close">
                    <Icon type="ios-close" size="31" class="ivu-icon-ios-close" />
                </a>
            </div>
        </div>
        <Form ref="form" :model="form" :label-width="100" :rules="formValidate" label-position="left">

            <FormItem label="设备名称" prop="title">
                <Input v-model="form.title" clearable show-word-limit maxlength="240" placeholder="请输入设备名称..." style="width:570px" />
            </FormItem>
            <FormItem label="厂家" prop="producer">
                <Input v-model="form.producer" clearable show-word-limit maxlength="240" placeholder="请输入设备生产厂家..." style="width:570px" />
            </FormItem>
            <FormItem label="生产日期" prop="productionDate">
                <DatePicker type="date" format="yyyy-MM-dd" @on-change="changeProductionDate" clearable :placeholder="form.productionDate" style="width:570px"></DatePicker>
            </FormItem>
            <FormItem label="单价" prop="unitMoney">
                <InputNumber v-model="form.unitMoney" min="0" max="5000000" placeholder="请输入设备单价" style="width:570px"></InputNumber>
            </FormItem>
            <FormItem label="注意事项" prop="attention">
                <Input v-model="form.attention" show-word-limit maxlength="240" type="textarea" :rows="4" placeholder="请输入注意事项..." clearable style="width:570px" />
            </FormItem>
            <FormItem label="照片" prop="image">
                <upload-pic-input v-model="form.image" placeholder="请上传设备图片..." style="width:570px"></upload-pic-input>
            </FormItem>
            <FormItem label="所属实验室" prop="laboratoryId">
                <Select v-model="form.laboratoryId" clearable placeholder="请选择所属实验室..." style="width:570px">
                    <Option v-for="(item,index) in laboratoryList" :key="index" :value="item.id">{{item.title}}</Option>
                </Select>
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
    editExperimentalEquipment,
    getLaboratoryList
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
                producer: "",
                productionDate: "",
                unitMoney: 0,
                attention: "",
                image: "",
                laboratoryId: "",
                laboratoryName: "",
            },
            // 表单验证规则
            formValidate: {},
            laboratoryList: []
        };
    },
    methods: {
        init() {
            this.getLaboratoryListFx();
            this.handleReset();
            this.form = this.data;
        },
        changeProductionDate(e) {
            this.form.productionDate = e;
        },
        getLaboratoryListFx() {
            var that = this;
            getLaboratoryList().then(res => {
                if (res.success) {
                    that.laboratoryList = res.result;
                }
            })
        },
        handleReset() {
            this.$refs.form.resetFields();
        },
        handleSubmit() {
            this.$refs.form.validate(valid => {
                if (valid) {
                    editExperimentalEquipment(this.form).then(res => {
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
