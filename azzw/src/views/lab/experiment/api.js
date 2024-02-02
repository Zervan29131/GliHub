import { getRequest, postRequest, putRequest, postBodyRequest, getNoAuthRequest, postNoAuthRequest } from '@/libs/axios';

export const getExperimentOne = (params) => {
    return getRequest('/experiment/getOne', params)
}
export const getExperimentList = (params) => {
    return getRequest('/experiment/getByPage', params)
}
export const getExperimentCount = (params) => {
    return getRequest('/experiment/count', params)
}
export const addExperiment = (params) => {
    return postRequest('/experiment/insert', params)
}
export const editExperiment = (params) => {
    return postRequest('/experiment/update', params)
}
export const addOrEditExperiment = (params) => {
    return postRequest('/experiment/insertOrUpdate', params)
}
export const deleteExperiment = (params) => {
    return postRequest('/experiment/delByIds', params)
}