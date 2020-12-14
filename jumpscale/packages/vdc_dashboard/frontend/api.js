// const axios = require('axios')
const baseURL = "/vdc_dashboard/api"

const apiClient = {
  content: {
    get: (url) => {
      return axios({
        url: url
      })
    }
  },
  admins: {
    getCurrentUser: () => {
      return axios({
        url: "/auth/authenticated/"
      })
    },
  },
  solutions: {
    getSolutions: (solutionType) => {
      return axios({
        url: `${baseURL}/deployments/${solutionType}`, // TODO Replace with bottle server api call
        method: "get",
      })
    },
    deleteSolution: (releaseName, solutionId, vdcName) => {
      return axios({
        url: `${baseURL}/deployments/cancel/`, // TODO Replace with bottle server api call
        method: "post",
        data: { release: releaseName, solution_id: solutionId, vdc_name: vdcName },
        headers: { 'Content-Type': 'application/json' }
      })
    },
    getVdcInfo: () => {
      return axios({
        url: `${baseURL}/threebot_vdc`,
        headers: { 'Content-Type': 'application/json' },
        method: "get"
      })
    },
    exposeS3: () => {
      return axios({
        url: `${baseURL}/s3/expose`,
        headers: { 'Content-Type': 'application/json' },
        method: "get"
      })
    },
  },
  license: {
    accept: () => {
      return axios({
        url: `${baseURL}/accept/`,
        method: "get"
      })
    },
  }
}
