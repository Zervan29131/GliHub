/**
 * Native Vue 3.5+ `<script setup name="...">` -> `defineOptions({ name: '...' })` transform
 * Eliminates legacy Vite 2 `vite-plugin-vue-setup-extend` peer conflicts on Vite 6+.
 */
export default function createSetupExtend() {
  return {
    name: 'glihub-vue35-setup-name',
    enforce: 'pre',
    transform(code, id) {
      if (!id.endsWith('.vue')) return null
      const match = code.match(/<script\s+[^>]*setup[^>]*\sname=["']([^"']+)["'][^>]*>/)
      if (!match || code.includes('defineOptions(')) return null
      const compName = match[1]
      const injected = code.replace(
        match[0],
        `${match[0]}\ndefineOptions({ name: '${compName}' })\n`
      )
      return { code: injected, map: null }
    }
  }
}
