import { config } from '@vue/test-utils'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// Global registration for Element Plus components used in tests
const app = createApp({})
app.use(ElementPlus)

// Make Element Plus available globally
config.global.plugins = [ElementPlus]
