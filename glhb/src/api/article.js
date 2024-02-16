
//导入request.js请求工具
import request from '@/utils/request.js'
// 六 2.4 导入@/stores/token.js
import { useTokenStore } from '@/stores/token.js'
 
// 六  文章分类列表查询函数  
export const articleCategoryListService = (registerData) =>{    
    // 六 2.4获取token状态
    // const tokenStore = useTokenStore()
    //通过请求头Authorization携带token
    // return request.get('/category', { headers: { 'Authorization': tokenStore.token } });
    return request.get('/category');
    
}