import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats').then(r => r.data)
export const getDashboardActivity = () => api.get('/dashboard/activity').then(r => r.data)

// Complaints
export const ingestComplaint = (data) => api.post('/complaints/ingest', data).then(r => r.data)
export const listComplaints = (params) => api.get('/complaints/', { params }).then(r => r.data)
export const getComplaint = (id) => api.get(`/complaints/${id}`).then(r => r.data)

// Lineages
export const listLineages = (params) => api.get('/lineages/', { params }).then(r => r.data)
export const getLineage = (id) => api.get(`/lineages/${id}`).then(r => r.data)
export const updateLineageStatus = (id, body) => api.patch(`/lineages/${id}/status`, body).then(r => r.data)

// Alerts
export const listAlerts = (params) => api.get('/alerts/', { params }).then(r => r.data)
export const generateAlerts = () => api.post('/alerts/generate').then(r => r.data)
export const updateAlert = (id, body) => api.patch(`/alerts/${id}`, body).then(r => r.data)

// Audit
export const listAuditLogs = (params) => api.get('/audit/', { params }).then(r => r.data)

// Cross-Bank
export const getCrossBank = () => api.get('/crossbank/').then(r => r.data)

// Admin
export const getAdminConfig = () => api.get('/admin/config').then(r => r.data)
export const updateAdminConfig = (body) => api.put('/admin/config', body).then(r => r.data)

// Dataset
export const getDatasetStatus = () => api.get('/dataset/status').then(r => r.data)
export const loadDataset = () => api.post('/dataset/load').then(r => r.data)

export default api
