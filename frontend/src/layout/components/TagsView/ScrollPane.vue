<template>
  <el-scrollbar
    ref="scrollContainer"
    :vertical="false"
    class="scroll-container"
    @wheel.prevent="handleScroll"
  >
    <slot />
  </el-scrollbar>
</template>

<script setup>
import useTagsViewStore from '@/store/modules/tagsView'

const tagAndTagSpacing = ref(4)
const scrollContainer = ref(null)
const emits = defineEmits(['scroll'])

const scrollWrapper = computed(() => {
  const inst = scrollContainer.value
  if (!inst) return null
  return inst.wrapRef || (inst.$refs && inst.$refs.wrap$) || null
})

const emitScroll = () => {
  emits('scroll')
}

onMounted(() => {
  if (scrollWrapper.value) {
    scrollWrapper.value.addEventListener('scroll', emitScroll, { passive: true })
  }
})

onBeforeUnmount(() => {
  if (scrollWrapper.value) {
    scrollWrapper.value.removeEventListener('scroll', emitScroll)
  }
})

function handleScroll(e) {
  const $scrollWrapper = scrollWrapper.value
  if (!$scrollWrapper) return
  const eventDelta = e.wheelDelta || -e.deltaY * 40
  $scrollWrapper.scrollLeft = $scrollWrapper.scrollLeft + eventDelta / 4
}

const tagsViewStore = useTagsViewStore()
const visitedViews = computed(() => tagsViewStore.visitedViews)

function moveToTarget(currentTag) {
  const containerEl = scrollContainer.value?.$el
  const $scrollWrapper = scrollWrapper.value
  if (!containerEl || !$scrollWrapper) return

  const $containerWidth = containerEl.offsetWidth
  let firstTag = null
  let lastTag = null

  if (visitedViews.value.length > 0) {
    firstTag = visitedViews.value[0]
    lastTag = visitedViews.value[visitedViews.value.length - 1]
  }

  if (firstTag === currentTag) {
    $scrollWrapper.scrollLeft = 0
  } else if (lastTag === currentTag) {
    $scrollWrapper.scrollLeft = $scrollWrapper.scrollWidth - $containerWidth
  } else {
    const tagListDom = document.getElementsByClassName('tags-view-item')
    const currentIndex = visitedViews.value.findIndex(item => item === currentTag)
    if (currentIndex <= 0 || currentIndex >= visitedViews.value.length - 1) return

    let prevTag = null
    let nextTag = null
    for (let i = 0; i < tagListDom.length; i++) {
      const dom = tagListDom[i]
      if (dom.dataset?.path === visitedViews.value[currentIndex - 1]?.path) {
        prevTag = dom
      }
      if (dom.dataset?.path === visitedViews.value[currentIndex + 1]?.path) {
        nextTag = dom
      }
    }

    if (!nextTag || !prevTag) return
    const afterNextTagOffsetLeft = nextTag.offsetLeft + nextTag.offsetWidth + tagAndTagSpacing.value
    const beforePrevTagOffsetLeft = prevTag.offsetLeft - tagAndTagSpacing.value
    if (afterNextTagOffsetLeft > $scrollWrapper.scrollLeft + $containerWidth) {
      $scrollWrapper.scrollLeft = afterNextTagOffsetLeft - $containerWidth
    } else if (beforePrevTagOffsetLeft < $scrollWrapper.scrollLeft) {
      $scrollWrapper.scrollLeft = beforePrevTagOffsetLeft
    }
  }
}

defineExpose({
  moveToTarget
})
</script>

<style lang="scss" scoped>
.scroll-container {
  white-space: nowrap;
  position: relative;
  overflow: hidden;
  width: 100%;
  :deep(.el-scrollbar__bar) {
    bottom: 0px;
  }
  :deep(.el-scrollbar__wrap) {
    height: 49px;
  }
}
</style>
