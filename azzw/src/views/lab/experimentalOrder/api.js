import { getRequest, postRequest, putRequest, postBodyRequest, getNoAuthRequest, postNoAuthRequest } from '@/libs/axios';

export const getExperimentalOrderOne = (params) => {
    return getRequest('/experimentalOrder/getOne', params)
}
export const getExperimentalOrderList = (params) => {
    return getRequest('/experimentalOrder/getByPage', params)
}
export const getExperimentalOrderCount = (params) => {
    return getRequest('/experimentalOrder/count', params)
}
export const addExperimentalOrder = (params) => {
    return postRequest('/experimentalOrder/insert', params)
}
export const editExperimentalOrder = (params) => {
    return postRequest('/experimentalOrder/update', params)
}
export const addOrEditExperimentalOrder = (params) => {
    return postRequest('/experimentalOrder/insertOrUpdate', params)
}
export const deleteExperimentalOrder = (params) => {
    return postRequest('/experimentalOrder/delByIds', params)
}
export const fangOrder = (params) => {
    return getRequest('/experimentalOrder/fangOrder', params)
}
export const getLaboratoryList = (params) => {
    return getRequest('/laboratory/getAll', params)
}
export const getExperimentList = (params) => {
    return getRequest('/experiment/getAll', params)
}
export const addOrder = (params) => {
    return postRequest('/experimentalOrder/order', params)
}