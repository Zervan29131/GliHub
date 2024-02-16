#  一、环境准备

### 1.1 创建工程

```js
npm init vue@latest
npm install
```

### 1.2 安装插件

1. 安装element-plus

   ```js
   1.1 执行命令: npm install element-plus --save
   1.2 在main.js中做如下配置
   	import ElementPlus from 'element-plus'
   	import 'element-plus/dist/index.css'
   	app.use(ElementPlus)
   ```

2. 安装axios

   ```js
   npm install axios
   ```

3. 安装sass依赖

   ```js
   npm install sass -D
   ```

# 二、页面搭建

### 2.1 最终页面

```html
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

//调用后台接口，完成注册接口调用
import { userRegisterService,userLoginService } from '@/api/user'
//用于注册的事件函数
const register = async () => {
  //console.log('注册...');
  //register是一个响应式的对象，需要加.value才可以获取值
  let result = await userRegisterService(registerData.value);
  if (result.code == 1) {
    alert(result.msg?result.msg :'注册成功!')
  } else {
    alert('注册失败!')
  }
}
const login = async () => {
  //console.log('注册...');
  //register是一个响应式的对象，需要加.value才可以获取值
  let result = await userLoginService(registerData.value);
  if (result.code == 1) {
    alert(result.msg?result.msg :'登录成功!')
  } else {
    alert('登录失败!')
  }
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
```

### 2.2 绑定数据与事件

#### 2.2.1 数据绑定

每次点击注册或者登录，共用数据模型中的数据

```js
//用于注册的数据模型
const registerData = ref({
    username: '',
    password: '',
    rePassword: ''
})
//清空数据模型的数据
const clearRegisterData = () => {
    registerData.value = {
        username: '',
        password: '',
        rePassword: ''
    }
}
```

#### 2.2.2 表单校验

el-form标签上通过rules属性，绑定校验规则

el-form-item标签上通过prop属性，指定校验项

```js
//自定义确认密码的校验函数
const rePasswordValid = (rule, value, callback) => {
  if (value == null || value === "") {
    return callback(new Error("请再次确认密码"));
  }else if (registerData.value.password !== value) {
//registerData是响应式对象，需要加上.value才能校验通过
    return callback(new Error("两次输入密码不一致"));
  }else {
    return callback;
  }};
//用于注册的表单校验模型
const registerDataRules = ref({
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 5, max: 16, message: '用户名的长度必须为5~16位', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 5, max: 16, message: '密码长度必须为5~16位', trigger: 'blur' }
    ],
    rePassword: [
        { validator: rePasswordValid, trigger: 'blur' }
    ]
})
```

#### 2.2.3 事件绑定

```js
const register = async () => {
    //console.log('注册...');
    //register是一个响应式的对象，需要加.value才可以获取值
    let result = await userRegisterService(registerData.value);
    if (result.code == 0) {
        alert('注册成功!')
    } else {
        alert('注册失败!')
    }
}
const login = async () => {
    //console.log('注册...');
    //register是一个响应式的对象，需要加.value才可以获取值
    let result = await userRegisterService(registerData.value);
    if (result.code == 0) {
        alert('登录成功!')
    } else {
        alert('登录失败!')
    }
}
```



### 2.3 调用后台接口

#### 2.3.1 在src/api/user.js中提供访问注册和登录接口的函数

```js
//导入request.js请求工具
import request from "@/utils/request"

//提供注册接口的函数，接口调用的js文件中接口调用都说以service结尾的
export const userRegisterService = (registerData) => {
    //借助于URLSearchParams完成参数传递
    var params = new URLSearchParams()
    for (let key in registerData) {
        params.append(key, registerData[key])
    }
    return request.post('/user/register', params)
}
//登录
export const loginService = (loginData)=>{
    var params = new URLSearchParams()
    for(let key in loginData){
        params.append(key,loginData[key])
    }
    return request.post('/user/login',params)
}
```

#### 2.3.2 在Login.vue中完成接口调用

```js
import { registerService, loginService } from '@/api/user.js'

//用于注册的事件函数
const register = async () => {
    //console.log('注册...');
    //register是一个响应式的对象，需要加.value才可以获取值
    let result = await userRegisterService(registerData.value);
    if (result.code == 0) {
        alert('注册成功!')
    } else {
        alert('注册失败!')
    }
}
//用于登录的事件函数
const login = async () => {
    //console.log('注册...');
    //register是一个响应式的对象，需要加.value才可以获取值
    let result = await userRegisterService(registerData.value);
    if (result.code == 0) {
        alert('登录成功!')
    } else {
        alert('登录失败!')
    }
}
```

### 2.4 处理跨域问题

由于发起ajax请求的域为http://localhost:5173, 而后台服务器的域为 http://localhost:8080, 所以浏览器会限制该请求的发送, 这种问题称为跨域问题, 跨域问题可以在服务器端解决,也可以在浏览器端解决, 咱们这一块通过配置代理的方式解决

启动redies，执行以下命令

```
redis-service
```

启动jar包

```
java -jar (url)
```

**request.js中配置统一前缀 /api**

```js
//定制请求的实例

//导入axios  npm install axios
import axios from "axios";
//定义一个变量,记录公共的前缀  ,  baseURL
// const baseURL = 'http://localhost:8080';
const baseURL = '/api';
const instance = axios.create({ baseURL });

//添加响应拦截器
instance.interceptors.response.use(
  (result) => {
    // 判断业务状态码
    if (result.data.code === 1) {
      //成功，正常返回数据
      return result.data;
    }
    // 操作失败
    alert(result.data.msg ? result.data.msg : "服务异常");
    // 异步操作的状态转换为失败
    return Promise.reject(result.data);
  },
//   (err) => {
    err => {
    alert("服务异常");
    return Promise.reject(err); //异步的状态转化成失败的状态
  }
);

export default instance;
```

**vie.config.js中配置代理**

```js
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  //配置代理
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080', // 后端服务器地址
        changeOrigin: true, // 是否改变请求域名
        rewrite: (path) => path.replace(/^\/api/, '')//将原有请求路径中的api替换为''
      }
    }
  }
})
```

### 2.5 优化axios响应截器

在接口调用的API中，我们都需要对业务响应的状态进行判断，从而给用户对应的提示，这个工作不难，但是每个接口的调用，都这样写代码，显然是比较繁琐的，我们可以在axios的相应拦截器中，如果服务器响应成功了，统一判断后台返回的业务状态码code，如果成功了，正常返回数据，如果失败了，则给出用户对应的提示即可

**请求工具request.js**

```js
//定制请求的实例

//导入axios  npm install axios
import axios from "axios";
//定义一个变量,记录公共的前缀  ,  baseURL
// const baseURL = 'http://localhost:8080';
const baseURL = '/api';
const instance = axios.create({ baseURL });

//添加响应拦截器
instance.interceptors.response.use(
  (result) => {
    // 判断业务状态码
    if (result.data.code === 1) {
      //成功，正常返回数据
      return result.data;
    }
    // 操作失败
    // alert(result.data.msg ? result.data.msg : "服务异常");
    //优化alert
    ElMessage.error(result.data.msg?result.data.msg : '服务异常')
    // 异步操作的状态转换为失败
    return Promise.reject(result.data);
  },
//   (err) => {
    err => {
    alert("服务异常");
    return Promise.reject(err); //异步的状态转化成失败的状态
  }
);
export default instance;
```

**Element-Plus提示框的使用**

```js
import { ElMessage } from 'element-plus'
    ElMessage.success(result.msg?result.msg : '登录成功')
    ElMessage.success(result.msg?result.msg : '注册成功')
    ElMessage.error(result.data.msg?result.data.msg : '服务异常')
ElMessage.error('服务异常');
ElMessage.success('登录成功!')
```
