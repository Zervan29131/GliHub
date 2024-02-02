import { getRequest, postRequest, putRequest, postBodyRequest, getNoAuthRequest, postNoAuthRequest } from '@/libs/axios';

export const getLaboratoryTypeOne = (params) => {
    return getRequest('/laboratoryType/getOne', params)
}
export const getLaboratoryTypeList = (params) => {
    return getRequest('/laboratoryType/getByPage', params)
}
export const getLaboratoryTypeCount = (params) => {
    return getRequest('/laboratoryType/count', params)
}
export const addLaboratoryType = (params) => {
    return postRequest('/laboratoryType/insert', params)
}
export const editLaboratoryType = (params) => {
    return postRequest('/laboratoryType/update', params)
}
export const addOrEditLaboratoryType = (params) => {
    return postRequest('/laboratoryType/insertOrUpdate', params)
}
export const deleteLaboratoryType = (params) => {
    return postRequest('/laboratoryType/delByIds', params)
}