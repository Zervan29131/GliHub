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
export const userLoginService = (loginData)=>{
    var params = new URLSearchParams()
    for(let key in loginData){
        params.append(key,loginData[key])
    }
    return request.post('/user/login',params)
}
