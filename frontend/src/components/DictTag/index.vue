<template>
  <div>
    <template v-for="(item, index) in (options || [])">
      <template v-if="values.includes(String(item.value))">
        <span
          v-if="!item.elTagType || item.elTagType === 'default'"
          :key="item.value"
          :index="index"
          :class="item.elTagClass"
        >{{ item.label }}</span>
        <el-tag
          v-else
          :key="item.value + ''"
          :disable-transitions="true"
          :index="index"
          :type="normalizeTagType(item.elTagType)"
          :class="item.elTagClass"
        >{{ item.label }}</el-tag>
      </template>
    </template>
  </div>
</template>

<script setup>
const props = defineProps({
  options: {
    type: Array,
    default: () => []
  },
  value: [Number, String, Array]
})

const VALID_TYPES = new Set(['primary', 'success', 'info', 'warning', 'danger'])

function normalizeTagType(raw) {
  return VALID_TYPES.has(raw) ? raw : 'primary'
}

const values = computed(() => {
  if (props.value !== null && typeof props.value !== 'undefined') {
    return Array.isArray(props.value) ? props.value.map(String) : [String(props.value)]
  }
  return []
})
</script>

<style scoped>
.el-tag + .el-tag {
  margin-left: 10px;
}
</style>
