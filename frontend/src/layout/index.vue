<template>
  <div :class="classObj" class="app-wrapper" :style="{ '--current-color': theme }">
    <div v-if="device === 'mobile' && sidebar.opened" class="drawer-bg" @click="handleClickOutside" />
    <sidebar v-if="!sidebar.hide" class="sidebar-container" />
    <div :class="{ hasTagsView: needTagsView, sidebarHide: sidebar.hide }" class="main-container">
      <div :class="{ 'fixed-header': fixedHeader }">
        <navbar @setLayout="setLayout" />
        <tags-view v-if="needTagsView" />
      </div>
      <app-main />
      <settings ref="settingRef" />
      <ehs-ai-copilot />
    </div>
  </div>
</template>

<script setup>
import { useWindowSize } from '@vueuse/core'
import Sidebar from './components/Sidebar/index.vue'
import { AppMain, Navbar, Settings, TagsView } from './components'
import EhsAiCopilot from '@/components/EhsAiCopilot/index.vue'

import useAppStore from '@/store/modules/app'
import useSettingsStore from '@/store/modules/settings'

const route = useRoute()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

const theme = computed(() => settingsStore.theme)
const sidebar = computed(() => appStore.sidebar)
const device = computed(() => appStore.device)
const needTagsView = computed(() => settingsStore.tagsView)
const fixedHeader = computed(() => settingsStore.fixedHeader)

const classObj = computed(() => ({
  hideSidebar: !sidebar.value.opened,
  openSidebar: sidebar.value.opened,
  withoutAnimation: sidebar.value.withoutAnimation,
  mobile: device.value === 'mobile'
}))

const { width } = useWindowSize()
const WIDTH = 992

// 仅在窗口宽度跨越断点时切换桌面/移动端模式，避免点击展开菜单时被反向立即关闭
watch(
  width,
  (val) => {
    if (val - 1 < WIDTH) {
      if (device.value !== 'mobile') {
        appStore.toggleDevice('mobile')
        appStore.closeSideBar(true)
      }
    } else if (device.value !== 'desktop') {
      appStore.toggleDevice('desktop')
    }
  },
  { immediate: true }
)

// 移动端模式下点击菜单完成路由跳转后自动收起侧边抽屉
watch(
  () => route.path,
  () => {
    if (device.value === 'mobile' && sidebar.value.opened) {
      appStore.closeSideBar(false)
    }
  }
)

function handleClickOutside() {
  appStore.closeSideBar(false)
}

const settingRef = ref(null)
function setLayout() {
  settingRef.value?.openSetting()
}
</script>

<style lang="scss" scoped>
@import "@/assets/styles/mixin.scss";
@import "@/assets/styles/variables.module.scss";

.app-wrapper {
  @include clearfix;
  position: relative;
  height: 100%;
  width: 100%;

  &.mobile.openSidebar {
    position: fixed;
    top: 0;
  }
}

.drawer-bg {
  background: #000;
  opacity: 0.3;
  width: 100%;
  top: 0;
  height: 100%;
  position: fixed;
  z-index: 999;
}

.fixed-header {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 9;
  width: calc(100% - #{$base-sidebar-width});
  transition: width 0.28s;
}

.hideSidebar .fixed-header {
  width: calc(100% - 54px);
}

.sidebarHide .fixed-header {
  width: 100%;
}

.mobile .fixed-header {
  width: 100%;
}
</style>
