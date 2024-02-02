import { getRequest, postRequest, putRequest, postBodyRequest, getNoAuthRequest, postNoAuthRequest } from '@/libs/axios';

export const getLaboratoryOne = (params) => {
    return getRequest('/laboratory/getOne', params)
}
export const getLaboratoryList = (params) => {
    return getRequest('/laboratory/getByPage', params)
}
export const getLaboratoryCount = (params) => {
    return getRequest('/laboratory/count', params)
}
export const addLaboratory = (params) => {
    return postRequest('/laboratory/insert', params)
}
export const editLaboratory = (params) => {
    return postRequest('/laboratory/update', params)
}
export const addOrEditLaboratory = (params) => {
    return postRequest('/laboratory/insertOrUpdate', params)
}
export const deleteLaboratory = (params) => {
    return postRequest('/laboratory/delByIds', params)
}
export const getLaboratoryTypeList = (params) => {
    return getRequest('/laboratoryType/getAll', params)
}
export const getUserList = (params) => {
    return getRequest('/superUser/getAll', params)
}
export const getEquipmentList = (params) => {
    return getRequest('/experimentalEquipment/getAllByLaboratory', params)
}
