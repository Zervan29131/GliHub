<template>
  <div class="login">
    <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form" autocomplete="off" @submit.prevent>
      <h3 class="title">GliHub 3.0 工业安全风控与应急决策平台</h3>
      <el-form-item prop="username">
        <el-input
          v-model="loginForm.username"
          type="text"
          size="large"
          name="glihub_account"
          autocomplete="off"
          spellcheck="false"
          placeholder="账号"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="user" class="el-input__icon input-icon" /></template>
        </el-input>
      </el-form-item>
      <el-form-item prop="password">
        <!-- 使用受控文本掩码替代原生 type="password"，彻底避免浏览器弱口令/数据泄露弹窗遮挡界面 -->
        <el-input
          v-model="loginForm.password"
          type="text"
          size="large"
          name="glihub_credential"
          autocomplete="off"
          spellcheck="false"
          :class="{ 'pwd-masked': pwdMasked }"
          placeholder="密码"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="password" class="el-input__icon input-icon" /></template>
          <template #suffix>
            <el-icon class="pwd-toggle-icon" @click="pwdMasked = !pwdMasked">
              <View v-if="!pwdMasked" />
              <Hide v-else />
            </el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item v-if="captchaEnabled" prop="code">
        <el-input
          v-model="loginForm.code"
          size="large"
          autocomplete="off"
          placeholder="请输入右侧算术结果"
          style="width: 63%"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="validCode" class="el-input__icon input-icon" /></template>
        </el-input>
        <div class="login-code">
          <img v-if="codeUrl" :src="codeUrl" title="点击刷新验证码" class="login-code-img" @click="getCode" />
        </div>
      </el-form-item>
      <div class="login-options">
        <el-checkbox v-model="loginForm.rememberMe">记住登录状态</el-checkbox>
      </div>
      <el-form-item style="width: 100%;">
        <el-button :loading="loading" size="large" type="primary" style="width: 100%;" @click.prevent="handleLogin">
          <span v-if="!loading">登 录</span>
          <span v-else>登 录 中...</span>
        </el-button>
      </el-form-item>
    </el-form>
    <div class="el-login-footer">
      <span>Copyright © 2024-2026 GliHub 3.0 All Rights Reserved.</span>
    </div>
  </div>
</template>

<script setup name="Login">
import { getCodeImg } from '@/api/login'
import Cookies from 'js-cookie'
import { encrypt, decrypt } from '@/utils/jsencrypt'
import useUserStore from '@/store/modules/user'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const loginRef = ref(null)

const loginForm = ref({
  username: 'admin',
  password: '',
  rememberMe: false,
  code: '',
  uuid: ''
})

const loginRules = {
  username: [{ required: true, trigger: 'blur', message: '请输入您的账号' }],
  password: [{ required: true, trigger: 'blur', message: '请输入您的密码' }],
  code: [{ required: true, trigger: 'change', message: '请输入验证码计算结果' }]
}

const codeUrl = ref('')
const loading = ref(false)
const pwdMasked = ref(true)
const captchaEnabled = ref(true)
const redirect = ref(undefined)

watch(
  route,
  (newRoute) => {
    redirect.value = newRoute.query && newRoute.query.redirect
  },
  { immediate: true }
)

function handleLogin() {
  if (!loginRef.value || loading.value) return
  loginRef.value.validate(valid => {
    if (!valid) return
    loading.value = true
    if (loginForm.value.rememberMe) {
      Cookies.set('username', loginForm.value.username, { expires: 30 })
      Cookies.set('password', encrypt(loginForm.value.password), { expires: 30 })
      Cookies.set('rememberMe', String(loginForm.value.rememberMe), { expires: 30 })
    } else {
      Cookies.remove('username')
      Cookies.remove('password')
      Cookies.remove('rememberMe')
    }
    userStore
      .login(loginForm.value)
      .then(() => {
        const target = redirect.value && redirect.value !== '/login' ? redirect.value : '/'
        router.push(target)
      })
      .catch(() => {
        loading.value = false
        loginForm.value.code = ''
        if (captchaEnabled.value) {
          getCode()
        }
      })
  })
}

function getCode() {
  getCodeImg()
    .then(res => {
      const enabled = res.captchaEnabled ?? res.captchaOnOff ?? true
      captchaEnabled.value = Boolean(enabled)
      if (captchaEnabled.value && res.img) {
        codeUrl.value = 'data:image/gif;base64,' + res.img
        loginForm.value.uuid = res.uuid || ''
      }
    })
    .catch(() => {})
}

function getCookie() {
  const username = Cookies.get('username')
  const password = Cookies.get('password')
  const rememberMe = Cookies.get('rememberMe')
  let decryptedPwd = loginForm.value.password
  if (password) {
    try {
      decryptedPwd = decrypt(password) || ''
    } catch (_) {
      decryptedPwd = ''
    }
  }
  loginForm.value = {
    username: username === undefined ? loginForm.value.username : username,
    password: decryptedPwd,
    rememberMe: rememberMe === undefined ? false : rememberMe === 'true',
    code: '',
    uuid: loginForm.value.uuid || ''
  }
}

getCookie()
getCode()
</script>

<style lang="scss" scoped>
.login {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-image: url("../assets/images/login-background.jpg");
  background-size: cover;
  background-position: center;
}

.title {
  margin: 0 auto 26px auto;
  text-align: center;
  color: #1e293b;
  font-size: 19px;
  font-weight: 700;
}

.login-form {
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.97);
  width: 420px;
  padding: 30px 30px 10px 30px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);

  .el-input {
    height: 40px;

    input {
      height: 40px;
    }
  }

  .input-icon {
    height: 39px;
    width: 14px;
    margin-left: 0;
  }
}

.pwd-masked :deep(.el-input__inner) {
  -webkit-text-security: disc;
  text-security: disc;
}

.pwd-toggle-icon {
  cursor: pointer;
  color: #909399;
  font-size: 16px;
  &:hover {
    color: #409eff;
  }
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 0 20px 0;
}

.login-code {
  width: 34%;
  height: 40px;
  float: right;
  display: flex;
  align-items: center;
  justify-content: flex-end;

  img {
    cursor: pointer;
    vertical-align: middle;
    border-radius: 4px;
  }
}

.login-code-img {
  height: 40px;
  width: 100%;
  object-fit: cover;
}

.el-login-footer {
  height: 40px;
  line-height: 40px;
  position: fixed;
  bottom: 0;
  width: 100%;
  text-align: center;
  color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 12px;
  letter-spacing: 1px;
  pointer-events: none;
}
</style>
