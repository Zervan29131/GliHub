import { getRequest, postRequest, putRequest, postBodyRequest, getNoAuthRequest, postNoAuthRequest } from '@/libs/axios';

export const getExperimentalEquipmentOne = (params) => {
    return getRequest('/experimentalEquipment/getOne', params)
}
export const getExperimentalEquipmentList = (params) => {
    return getRequest('/experimentalEquipment/getByPage', params)
}
export const getExperimentalEquipmentCount = (params) => {
    return getRequest('/experimentalEquipment/count', params)
}
export const addExperimentalEquipment = (params) => {
    return postRequest('/experimentalEquipment/insert', params)
}
export const editExperimentalEquipment = (params) => {
    return postRequest('/experimentalEquipment/update', params)
}
export const addOrEditExperimentalEquipment = (params) => {
    return postRequest('/experimentalEquipment/insertOrUpdate', params)
}
export const deleteExperimentalEquipment = (params) => {
    return postRequest('/experimentalEquipment/delByIds', params)
}
export const getLaboratoryList = (params) => {
    return getRequest('/laboratory/getAll', params)
}