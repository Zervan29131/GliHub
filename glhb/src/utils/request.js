//定制请求的实例

//导入axios  npm install axios
import axios from "axios";
//定义一个变量,记录公共的前缀  ,  baseURL
// const baseURL = 'http://localhost:8080';
const baseURL = '/api';
const instance = axios.create({ baseURL });

//六  3 添加请求拦截器
instance.interceptors.request.use(
  (config)=>{
      //在发送请求之前做什么
      let tokenStore = useTokenStore()
      //如果token中有值，在携带
      if(tokenStore.token){
          config.headers.Authorization=tokenStore.token
      }
      return config
  },
  (err)=>{
      //如果请求错误做什么
      Promise.reject(err)
  }
)

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
