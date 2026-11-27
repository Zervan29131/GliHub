<template>
  <div :class="{ 'show': show }" class="header-search">
    <svg-icon class-name="search-icon" icon-class="search" @click.stop="click" />
    <el-select
      ref="headerSearchSelectRef"
      v-model="search"
      :remote-method="querySearch"
      filterable
      default-first-option
      remote
      placeholder="搜索页面 / 功能菜单"
      class="header-search-select"
      @change="change"
    >
      <el-option
        v-for="option in options"
        :key="option.item.path"
        :value="option.item.path"
        :label="option.item.title.join(' > ')"
      />
    </el-select>
  </div>
</template>

<script setup>
import Fuse from 'fuse.js'
import { getNormalPath } from '@/utils/glihub'
import { isHttp } from '@/utils/validate'
import usePermissionStore from '@/store/modules/permission'

const search = ref('')
const options = ref([])
const searchPool = ref([])
const show = ref(false)
const fuse = ref(null)
const headerSearchSelectRef = ref(null)
const router = useRouter()
const routes = computed(() => usePermissionStore().routes)

function click() {
  show.value = !show.value
  if (show.value) {
    headerSearchSelectRef.value?.focus()
  }
}

function close() {
  headerSearchSelectRef.value?.blur()
  options.value = []
  show.value = false
}

function change(path) {
  if (!path) return
  if (isHttp(path)) {
    const pindex = path.indexOf('http')
    window.open(path.slice(pindex), '_blank')
  } else {
    router.push(path)
  }
  search.value = ''
  options.value = []
  nextTick(() => {
    show.value = false
  })
}

function initFuse(list) {
  fuse.value = new Fuse(list || [], {
    shouldSort: true,
    threshold: 0.4,
    location: 0,
    distance: 100,
    minMatchCharLength: 1,
    keys: [
      { name: 'title', weight: 0.7 },
      { name: 'path', weight: 0.3 }
    ]
  })
}

function generateRoutes(routeList, basePath = '', prefixTitle = []) {
  let res = []
  for (const r of routeList || []) {
    if (r.hidden) continue
    const p = r.path && r.path.length > 0 && r.path[0] === '/' ? r.path : '/' + (r.path || '')
    const data = {
      path: !isHttp(r.path) ? getNormalPath(basePath + p) : r.path,
      title: [...prefixTitle]
    }
    if (r.meta && r.meta.title) {
      data.title = [...data.title, r.meta.title]
      if (r.redirect !== 'noRedirect') {
        res.push(data)
      }
    }
    if (r.children) {
      const tempRoutes = generateRoutes(r.children, data.path, data.title)
      if (tempRoutes.length >= 1) {
        res = [...res, ...tempRoutes]
      }
    }
  }
  return res
}

function querySearch(query) {
  if (query !== '' && fuse.value) {
    options.value = fuse.value.search(query)
  } else {
    options.value = []
  }
}

watchEffect(() => {
  searchPool.value = generateRoutes(routes.value)
})

watch(
  searchPool,
  (list) => {
    initFuse(list)
  },
  { immediate: true }
)

watch(show, (value) => {
  if (value) {
    document.body.addEventListener('click', close)
  } else {
    document.body.removeEventListener('click', close)
  }
})
</script>

<style lang="scss" scoped>
.header-search {
  font-size: 0 !important;

  .search-icon {
    cursor: pointer;
    font-size: 18px;
    vertical-align: middle;
  }

  .header-search-select {
    font-size: 18px;
    transition: width 0.2s;
    width: 0;
    min-width: 0 !important;
    overflow: hidden;
    background: transparent;
    border-radius: 0;
    display: inline-block;
    vertical-align: middle;

    :deep(.el-input__inner) {
      border-radius: 0;
      border: 0;
      padding-left: 0;
      padding-right: 0;
      box-shadow: none !important;
      border-bottom: 1px solid #d9d9d9;
      vertical-align: middle;
    }
  }

  &.show {
    .header-search-select {
      width: 210px;
      margin-left: 10px;
    }
  }
}
</style>
