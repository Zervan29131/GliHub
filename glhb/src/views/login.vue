<script setup>
import { User, Lock } from "@element-plus/icons-vue";
import { ref } from "vue";
//控制注册与登录表单的显示， 默认显示注册
const isRegister = ref(false);

//用于注册的数据模型(接口文档)
const registerData = ref({
  username: "",
  password: "",
  rePassword: "",
});
//清空数据模型的数据
const clearRegisterData = () => {
  registerData.value = {
    username: '',
    password: '',
    rePassword: ''
  }
}

//自定义确认密码的校验函数
const rePasswordValid = (rule, value, callback) => {
  if (value == null || value === "") {
    return callback(new Error("请再次确认密码"));
  } else if (registerData.value.password !== value) {
    //registerData是响应式对象，需要加上.value才能校验通过
    return callback(new Error("两次输入密码不一致"));
  } else {
    return callback;//校验通过
  }
};
//用于注册的表单校验规则模型
const registerDataRules = ref({
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 5, max: 16, message: "用户名的长度必须为5~16位", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 5, max: 16, message: "密码长度必须为5~16位", trigger: "blur" },
  ],
  rePassword: [
    { validator: rePasswordValid, trigger: "blur" },
    //rePasswordValid需要重新自定义确认密码的校验函数
  ],
});
//Element-Plus提示框的使用,登录成功提示框的美化
import { ElMessage } from 'element-plus'

//调用后台接口，完成注册接口调用
import { userRegisterService,userLoginService } from '@/api/user'
//用于注册的事件函数
const register = async () => {
  //console.log('注册...');
  //register是一个响应式的对象，需要加.value才可以获取值
  let result = await userRegisterService(registerData.value);
  if (result.code == 1) {
    // alert(result.msg?result.msg :'注册成功!')
    //优化alert
    ElMessage.success(result.msg?result.msg : '注册成功')
  } 
  // else {
  //   alert('注册失败!')
  // }
}
const login = async () => {
  //console.log('注册...');
  //register是一个响应式的对象，需要加.value才可以获取值
  let result = await userLoginService(registerData.value);
  if (result.code == 1) {
    // alert(result.msg?result.msg :'登录成功!')
    //优化alert
    ElMessage.success(result.msg?result.msg : '登录成功')
  } 
  // else {
  //   alert('登录失败!')
  // }
}
</script>

<template>
  <el-row class="login-page">
    <el-col :span="12" class="bg"></el-col>
    <el-col :span="6" :offset="3" class="form">
      <!-- 注册表单 -->
      <el-form ref="form" size="large" autocomplete="off" v-if="isRegister" :model="registerData"
        :rules="registerDataRules">
        <el-form-item>
          <h1>注册</h1>
        </el-form-item>
        <el-form-item prop="username">
          <el-input :prefix-icon="User" placeholder="请输入用户名" v-model="registerData.username"></el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input :prefix-icon="Lock" type="password" placeholder="请输入密码" v-model="registerData.password"></el-input>
        </el-form-item>
        <el-form-item prop="rePassword">
          <el-input :prefix-icon="Lock" type="password" placeholder="请输入再次密码"
            v-model="registerData.rePassword"></el-input>
        </el-form-item>
        <!-- 注册按钮 -->
        <el-form-item>
          <el-button class="button" type="primary" auto-insert-space @click="register">
            注册
          </el-button>
        </el-form-item>
        <el-form-item class="flex">
          <el-link type="info" :underline="false" @click="isRegister = false;clearRegisterData()">
            ← 返回
          </el-link>
        </el-form-item>
      </el-form>
      <!-- 登录表单 -->
      <el-form ref="form" size="large" autocomplete="off" v-else :model="registerData" :rules="registerDataRules">
        <el-form-item>
          <h1>登录</h1>
        </el-form-item>
        <el-form-item prop="username">
          <el-input :prefix-icon="User" placeholder="请输入用户名(例如:admin)" v-model="registerData.username"></el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input name="password" :prefix-icon="Lock" type="password" placeholder="请输入密码(例如:123456)"
            v-model="registerData.password"></el-input>
        </el-form-item>
        <el-form-item class="flex">
          <div class="flex">
            <!-- <el-checkbox>记住我</el-checkbox> -->
            <!-- <el-link type="primary" :underline="false">
                        注册 →
                    </el-link> -->
            <el-link type="primary" :underline="false" @click="isRegister = true;clearRegisterData()">注册</el-link>
          </div>
        </el-form-item>
        <!-- 登录按钮 -->
        <el-form-item>
          <el-button class="button" type="primary" auto-insert-space @click="login">登录</el-button>
        </el-form-item>
        <el-form-item class="flex"> </el-form-item>
      </el-form>
    </el-col>
  </el-row>
</template>

<style lang="scss" scoped>
/* 样式 */
.login-page {
  height: 100vh;
  background-color: #fff;

  .bg {
    background: url("../assets/logo-bg.jpg") no-repeat 60% center / 240px auto,
      url("@/assets/login-bg.jpg") no-repeat center / cover;
    border-radius: 0 20px 20px 0;
  }

  .form {
    display: flex;
    flex-direction: column;
    justify-content: center;
    user-select: none;

    .title {
      margin: 0 auto;
    }

    .button {
      width: 100%;
    }

    .flex {
      width: 100%;
      display: flex;
      justify-content: space-between;
    }
  }
}
</style>
