<template>
  <div class="app-container home">
    <el-row :gutter="20">
      <el-col :sm="24" :lg="14">
        <el-card shadow="never" class="intro-card">
          <template #header>
            <div class="card-header">
              <span class="system-title">GliHub 安全评价与安全信息管理系统</span>
              <el-tag type="primary" effect="plain">v1.0.0</el-tag>
            </div>
          </template>
          <p class="intro-desc">
            面向危化品与工业企业场景的一体化安全评价与安全信息管理平台，集成<strong>生产场所、储存场所、公辅场所</strong>三大评价单元及四大标准评价模型计算程序，并提供作业区、特种设备、重大危险源详情、安全法律法规知识库与应急预案全流程管理。
          </p>
          <el-row :gutter="16" class="module-highlights">
            <el-col :span="12">
              <div class="highlight-box">
                <h4>安全评价管理</h4>
                <ul>
                  <li>评价单元联动检索（生产 / 储存 / 公辅场所）</li>
                  <li>道氏火灾爆炸指数法（F&amp;EI）定量计算</li>
                  <li>作业条件危险性分析法（LEC）分级判定</li>
                  <li>重大危险源事故后果模拟法（TNT 当量冲击波）</li>
                  <li>安全检查表法（SCL）标准核查与导出</li>
                </ul>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="highlight-box">
                <h4>安全信息管理</h4>
                <ul>
                  <li>作业区层级与员工安全职责档案</li>
                  <li>特种与安全设备台账及运行状态管理</li>
                  <li>危险源辨识、主要危险源详情与隐患排查</li>
                  <li>安全生产法律文献、技术标准知识库查阅</li>
                  <li>事故应急措施与救援预案在线管理</li>
                </ul>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <el-col :sm="24" :lg="10">
        <el-card shadow="never" class="tech-card">
          <template #header>
            <span class="section-title">技术栈架构</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="12">
              <h4>后端技术</h4>
              <ul>
                <li>Java &amp; Spring Boot 2.5</li>
                <li>Spring Security + JWT</li>
                <li>MyBatis + PageHelper</li>
                <li>PostgreSQL 关系型数据库</li>
                <li>Redis 会话与字典缓存</li>
                <li>Apache POI 报表导入导出</li>
              </ul>
            </el-col>
            <el-col :span="12">
              <h4>前端技术</h4>
              <ul>
                <li>Vue 3 (Composition API)</li>
                <li>Vite 构建工具</li>
                <li>Element Plus 组件库</li>
                <li>Pinia 状态管理</li>
                <li>Vue Router 动态权限路由</li>
                <li>Axios 请求拦截封装</li>
              </ul>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="Index">
</script>

<style scoped lang="scss">
.home {
  color: #606266;
  font-size: 14px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .system-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }

  .intro-desc {
    line-height: 1.8;
    margin: 0 0 16px;
    color: #4a4d52;
  }

  .highlight-box {
    background: #f8fafc;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 12px 16px;

    h4 {
      margin: 0 0 8px;
      color: #1f2f3d;
      font-size: 15px;
    }

    ul {
      padding-left: 18px;
      margin: 0;
      line-height: 1.9;
    }
  }

  .tech-card {
    h4 {
      margin: 0 0 10px;
      color: #1f2f3d;
    }

    ul {
      padding-left: 18px;
      margin: 0;
      line-height: 2;
    }
  }
}
</style>
