<template>
<div class="search">
    <add v-if="currView=='add'" @close="currView='index'" @submited="submited" />
    <edit v-if="currView=='edit'" @close="currView='index'" @submited="submited" :data="formData" />
    <Card v-show="currView=='index'">
        <Row v-show="openSearch" @keydown.enter.native="handleSearch">
            <Form ref="searchForm" :model="searchForm" inline :label-width="0">
                <Form-item ref="searchForm" :model="searchForm" inline :label-width="0" style="display:flex;">
                    <Form-item label="" prop="laboratoryId">
                        <Input type="text" v-model="searchForm.laboratoryId" placeholder="实验室ID" clearable style="width: 120px" />
                    </Form-item>
                    <Form-item label="" prop="experimentId">
                        <Input type="text" v-model="searchForm.experimentId" placeholder="实验ID" clearable style="width: 120px" />
                    </Form-item>
                    <Form-item style="margin-left:10px;" class="br">
                        <Button @click="handleSearch" type="primary" icon="ios-search" size="small" ghost>搜索</Button>
                        <Button @click="handleReset" type="warning" size="small" icon="md-refresh" ghost>重置</Button>
                        <Button @click="openAddOrderModalFx" type="info" size="small" icon="md-add" ghost :disabled="!$route.meta.permTypes.includes('add')">添加</Button>
                        <Button @click="delAll" type="error" icon="md-trash" size="small" ghost>删除</Button>
                        <Button @click="excelData" type="success" icon="md-paper-plane" size="small" ghost>导出</Button>
                    </Form-item>
                    <Form-item style="position:fixed;right:50px;top:130px">
                        <Button type="info" @click="showFilterPanelFlag = !showFilterPanelFlag" class="showFilterPanelFlag" icon="md-settings" size="small" ghost>
                            列筛选</Button>
                        <Button type="warning" @click="modal1 = true" class="showFilterPanelFlag" icon="ios-help-circle-outline" size="small" ghost>
                            使用教程</Button>
                        <Modal v-model="modal1" title="使用教程">
                            <p>1.XXXXXXXXXXXXXXXXXXXXXXXX</p>
                            <p>2.XXXXXXXXXXXXXXXXXXXXXXXX</p>
                            <p>3.XXXXXXXXXXXXXXXXXXXXXXXX</p>
                        </Modal>
                    </Form-item>
                </Form-item>
            </Form>
        </Row>
        <Row class="operation" style="position:relative;">
            <transition>
                <div v-show="showFilterPanelFlag" class="filter-panel">
                    <CheckboxGroup v-model="selected">
                        <div v-for="item in mycolumns" :key="item.key">
                            <Checkbox :label="item.title" style="margin: 2px 5px"></Checkbox>
                        </div>
                    </CheckboxGroup>
                </div>
            </transition>
        </Row>
        <Row v-show="openTip"> </Row>
        <Row :gutter="16">
            <Col span="24">
            <Table :loading="loading" :height="tableHeight" border stripe size="small" :columns="columns" :data="data" ref="table" sortable="custom" @on-sort-change="changeSort" @on-selection-change="changeSelect" @on-row-click="rowClick" :row-class-name="rowClassNmae"></Table>
            </Col>
        </Row>
        <Row type="flex" justify="end" class="page">
            <Page :current="searchForm.pageNumber" :total="total" :page-size="searchForm.pageSize" @on-change="changePage" @on-page-size-change="changePageSize" :page-size-opts="[15,20,50]" size="small" show-total show-elevator show-sizer></Page>
        </Row>
    </Card>
    <Modal v-model="addOrderModal" title="新增放号" :mask="false" footer-hide draggable width="1300">
        <Form :label-width="100" label-position="left">
            <Row :gutter="16">
                <Col span="12">
                <FormItem label="实验室">
                    <Select v-model="addOrderLaboratoryId" clearable placeholder="请选择实验室..." style="width:100%">
                        <Option v-for="(item,index) in laboratoryList" :key="index" :value="item.id">{{item.title}}</Option>
                    </Select>
                </FormItem>
                </Col>
                <Col span="12">
                <FormItem label="实验">
                    <Select v-model="addOrderExperimentId" clearable placeholder="请选择进行的实验..." style="width:100%">
                        <Option v-for="(item,index) in experimentList" :key="index" :value="item.id">{{item.title}}</Option>
                    </Select>
                </FormItem>
                </Col>
                <Col span="12">
                <FormItem label="日期">
                    <DatePicker type="date" format="yyyy-MM-dd" @on-change="changeAddOrderDate" clearable placeholder="请选择实验日期..." style="width:100%"></DatePicker>
                </FormItem>
                </Col>
                <Col span="12">
                <FormItem label="时段">
                    <Select v-model="addOrderStep" clearable placeholder="请选择进行的实验..." style="width:100%">
                        <Option value="上午">上午</Option>
                        <Option value="下午">下午</Option>
                        <Option value="晚上">晚上</Option>
                    </Select>
                </FormItem>
                </Col>
                <Col span="12">
                <FormItem label="放号数量">
                    <InputNumber :max="100" :min="1" v-model="addOrderSize"></InputNumber>
                </FormItem>
                </Col>
                <Col span="12">
                <FormItem label="价格">
                    <InputNumber :max="10000" :min="1" v-model="addOrderMoney"></InputNumber>
                </FormItem>
                </Col>
                <Col span="24">
                <Divider>
                    <Button :loading="addOrderLoading" type="success" @click="addOrderFx">确认放号</Button>
                </Divider>
                </Col>
            </Row>
        </Form>
    </Modal>
</div>
</template>

<script>
import {
    getExperimentalOrderList,
    deleteExperimentalOrder,
    fangOrder,
    getLaboratoryList,
    getExperimentList,
    addOrder
} from "./api.js";
import add from "./add.vue";
import edit from "./edit.vue";
export default {
    name: "single-window",
    components: {
        add,
        edit
    },
    data() {
        return {
            addOrderModal: false,
            addOrderDate: "",
            addOrderStep: "",
            addOrderMoney: 0,
            addOrderSize: 1,
            addOrderLaboratoryId: "",
            addOrderExperimentId: "",
            addOrderLoading: false,
            laboratoryList: [],
            experimentList: [],
            tableHeight: 0,
            selected: [
                "选择",
                "序号",
                "实验室名称",
                "实验名称",
                "日期",
                "时段",
                "顺序号",
                "是否预定",
                "预定时间",
                "下单人姓名",
                "手机号",
                "创建时间",
                "创建者",
                "修改时间",
                "修改者",
                "操作",
            ],
            modal1: false,
            openSearch: true, // 显示搜索
            openTip: true, // 显示提示
            formData: {},
            currView: "index",
            loading: true, // 表单加载状态
            searchForm: { // 搜索框初始化对象
                pageNumber: 1, // 当前页数
                pageSize: 15, // 页面大小
                sort: "createTime", // 默认排序字段
                order: "desc", // 默认排序方式
            },
            selectList: [], // 多选数据
            selectCount: 0, // 多选计数
            selectRow: 0,
            columns: [
                // 表头
                {
                    type: "selection",
                    width: 60,
                    title: "选择",
                    align: "center",
                    fixed: "left",
                },
                {
                    title: "序号",
                    width: 85,
                    align: "center",
                    fixed: "left",
                    sortType: true,
                    render: (h, params) => {
                        return h(
                            "span",
                            params.index +
                            (this.searchForm.pageNumber - 1) * this.searchForm.pageSize +
                            1
                        );
                    },
                },
                {
                    title: "实验室ID",
                    key: "laboratoryId",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "实验室名称",
                    key: "laboratoryName",
                    minWidth: 180,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "实验ID",
                    key: "experimentId",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "实验名称",
                    key: "experimentName",
                    minWidth: 180,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "日期",
                    key: "date",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "时段",
                    key: "step",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "顺序号",
                    key: "number",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "是否预定",
                    key: "orderFlag",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                    render: (h, params) => {
                        if (!params.row.orderFlag) {
                            return h("div", [
                                h(
                                    "span", {
                                        style: {
                                            color: "#3CB371",
                                        },
                                    },
                                    "未被预定"
                                ),
                            ]);
                        } else {
                            return h("div", [
                                h(
                                    "span", {
                                        style: {
                                            color: "#ff0000",
                                        },
                                    },
                                    "已被预定"
                                ),
                            ]);
                        }
                    },
                },
                {
                    title: "预定时间",
                    key: "orderTime",
                    minWidth: 180,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "下单人ID",
                    key: "userId",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "下单人姓名",
                    key: "userName",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "手机号",
                    key: "userMobile",
                    minWidth: 120,
                    tooltip: true,
                    sortable: false,
                },
                {
                    title: "创建时间",
                    key: "createTime",
                    sortable: true,
                    sortType: "desc",
                    minWidth: 180,
                    align: "center",
                    tooltip: true,
                },
                {
                    title: "创建者",
                    key: "createBy",
                    sortable: true,
                    sortType: "desc",
                    minWidth: 100,
                    align: "center",
                    tooltip: true,
                },
                {
                    title: "修改时间",
                    key: "updateTime",
                    minWidth: 180,
                    align: "center",
                    tooltip: true,
                },
                {
                    title: "修改者",
                    key: "updateBy",
                    minWidth: 100,
                    align: "center",
                    tooltip: true,
                },
                {
                    title: "操作",
                    key: "action",
                    align: "center",
                    width: 270,
                    fixed: "right",
                    render: (h, params) => {
                        var that = this;
                        return h("div", [
                            h(
                                "Button", {
                                    props: {
                                        type: "success",
                                        size: "small",
                                        icon: "ios-settings",
                                        ghost: true,
                                        disabled: params.row.orderFlag || !(that.$route.meta.permTypes && that.$route.meta.permTypes.includes("enable"))
                                    },
                                    style: {
                                        marginRight: "5px"
                                    },
                                    on: {
                                        click: () => {
                                            this.orderFx(params.row);
                                        }
                                    }
                                },
                                "预定"
                            ),
                            h(
                                "Button", {
                                    props: {
                                        type: "primary",
                                        size: "small",
                                        icon: "ios-create-outline",
                                        ghost: true
                                    },
                                    style: {
                                        marginRight: "5px"
                                    },
                                    on: {
                                        click: () => {
                                            this.edit(params.row);
                                        }
                                    }
                                },
                                "详情"
                            ),
                            h(
                                "Button", {
                                    props: {
                                        type: "error",
                                        size: "small",
                                        icon: "md-trash",
                                        ghost: true,
                                        disabled: params.row.orderFlag
                                    },
                                    on: {
                                        click: () => {
                                            this.remove(params.row);
                                        }
                                    }
                                },
                                "删除"
                            )
                        ]);
                    }
                }
            ],
            data: [], // 表单数据
            pageNumber: 1, // 当前页数
            pageSize: 10, // 页面大小
            total: 0, // 表单数据总数
            showFilterPanelFlag: false,
        };
    },
    methods: {
        init() {
            this.getDataList();
            this.getLaboratoryListFx();
            this.getExperimentListFx();
        },
        orderFx(e) {
            var that = this;
            addOrder({
                id: e.id
            }).then(res => {
                if (res.success) {
                    that.getDataList();
                    this.$Message.success("预定成功");
                }
            })
        },
        addOrderFx() {
            var that = this;
            that.addOrderLoading = true;
            fangOrder({
                laboratoryId: that.addOrderLaboratoryId,
                experimentId: that.addOrderExperimentId,
                date: that.addOrderDate,
                step: that.addOrderStep,
                size: that.addOrderSize,
                money: that.addOrderMoney
            }).then(res => {
                that.addOrderLoading = false;
                if (res.success) {
                    that.addOrderModal = false;
                    that.getDataList();
                    this.$Message.success("放号成功");
                }
            })
        },
        changeAddOrderDate(e) {
            this.addOrderDate = e;
        },
        openAddOrderModalFx() {
            this.addOrderDate = this.format(new Date(), "yyyy-MM-dd");
            this.addOrderStep = "上午";
            this.addOrderMoney = 0;
            this.addOrderLaboratoryId = "";
            this.addOrderExperimentId = "";
            this.addOrderModal = true;
        },
        getLaboratoryListFx() {
            var that = this;
            that.laboratoryList = []
            getLaboratoryList().then(res => {
                if (res.success) {
                    that.laboratoryList = res.result;
                }
            })
        },
        getExperimentListFx() {
            var that = this;
            that.experimentList = []
            getExperimentList().then(res => {
                if (res.success) {
                    that.experimentList = res.result;
                }
            })
        },
        submited() {
            this.currView = "index";
            this.getDataList();
        },
        changePage(v) {
            this.searchForm.pageNumber = v;
            this.getDataList();
            this.clearSelectAll();
        },
        changePageSize(v) {
            this.searchForm.pageSize = v;
            this.getDataList();
        },
        rowClick(row, index) {
            this.selectRow = row;
        },
        rowClassNmae(row, index) {
            if (row.id == this.selectRow.id) {
                return "rowClassNmaeColor";
            }
            return "";
        },
        excelData() {
            this.$refs.table.exportCsv({
                filename: "导出结果",
            });
        },
        handleSearch() {
            this.searchForm.pageNumber = 1;
            this.searchForm.pageSize = 15;
            this.getDataList();
        },
        handleReset() {
            this.$refs.searchForm.resetFields();
            this.searchForm.pageNumber = 1;
            this.searchForm.pageSize = 15;
            // 重新加载数据
            this.getDataList();
        },
        changeSort(e) {
            this.searchForm.sort = e.key;
            this.searchForm.order = e.order;
            if (e.order === "normal") {
                this.searchForm.order = "";
            }
            this.getDataList();
        },
        clearSelectAll() {
            this.$refs.table.selectAll(false);
        },
        changeSelect(e) {
            this.selectList = e;
            this.selectCount = e.length;
        },
        getDataList() {
            this.loading = true;
            getExperimentalOrderList(this.searchForm).then(res => {
                this.loading = false;
                if (res.success) {
                    this.data = res.result.records;
                    this.total = res.result.total;
                }
            });
        },
        add() {
            this.currView = "add";
        },
        edit(v) {
            // 转换null为""
            for (let attr in v) {
                if (v[attr] == null) {
                    v[attr] = "";
                }
            }
            let str = JSON.stringify(v);
            let data = JSON.parse(str);
            this.formData = data;
            this.currView = "edit";
        },
        remove(v) {
            this.$Modal.confirm({
                title: "确认删除",
                // 记得确认修改此处
                content: "您确认要删除 " + v.name + " ?",
                loading: true,
                onOk: () => {
                    // 删除
                    deleteExperimentalOrder({
                        ids: v.id
                    }).then(res => {
                        this.$Modal.remove();
                        if (res.success) {
                            this.$Message.success("操作成功");
                            this.getDataList();
                        }
                    });
                }
            });
        },
        delAll() {
            if (this.selectCount <= 0) {
                this.$Message.warning("您还未选择要删除的数据");
                return;
            }
            this.$Modal.confirm({
                title: "确认删除",
                content: "您确认要删除所选的 " + this.selectCount + " 条数据?",
                loading: true,
                onOk: () => {
                    let ids = "";
                    this.selectList.forEach(function (e) {
                        ids += e.id + ",";
                    });
                    ids = ids.substring(0, ids.length - 1);
                    // 批量删除
                    deleteExperimentalOrder({
                        ids: ids
                    }).then(res => {
                        this.$Modal.remove();
                        if (res.success) {
                            this.$Message.success("操作成功");
                            this.clearSelectAll();
                            this.getDataList();
                        }
                    });
                }
            });
        }
    },
    mounted() {
        this.init();
        this.tableHeight = Number(window.innerHeight - 273);
        this.mycolumns = this.columns;
        let showcolumns = [];
        for (var i = 0; i < this.selected.length; i++) {
            var item = this.selected[i];
            for (var j = 0; j < this.columns.length; j++) {
                if (this.columns[j].title == item) {
                    showcolumns.push(this.columns[j]);
                }
            }
        }
        this.columns = showcolumns;
    },
    watch: {
        selected: function (newcolumns) {
            let showcolumns = [];
            for (var i = 0; i < this.mycolumns.length; i++) {
                var item = this.mycolumns[i];
                if (item.title == undefined) showcolumns.push(item);
                else if (newcolumns.includes(item.title)) showcolumns.push(item);
            }
            this.columns = showcolumns;
        },
    },
};
</script>

<style lang="less">
// @import "../../../styles/table-common.less";
.search {
    .operation {
        margin-bottom: 2vh;
    }

    .select-count {
        font-weight: 600;
        color: #40a9ff;
    }

    .select-clear {
        margin-left: 10px;
    }

    .page {
        margin-top: 2vh;
    }

    .drop-down {
        margin-left: 5px;
    }
}

.filter-panel {
    width: 166px;
    min-height: 120px;
    height: 200px;
    position: absolute;
    background-color: white;
    z-index: 9999;
    margin-left: 1px;
    overflow-y: scroll;
    border: 1px solid blue;
    top: 35px;
    right: 10px;
}

.openSearch {
    position: absolute;
    right: 240px;
}

.openTip {
    position: absolute;
    right: 130px;
}

.showFilterPanelFlag {
    position: static !important;
    right: 10px;
    margin-right: 10px;
}

.ivu-table td {
    height: 38px !important;
}

.ivu-table-cell-with-expand {
    height: 38px !important;
    line-height: 38px !important;
}

.ivu-table .rowClassNmaeColor td {
    background-color: #b0b3b6 !important;
    color: #ffffff !important;
    font-size: 12px;
}
</style>
