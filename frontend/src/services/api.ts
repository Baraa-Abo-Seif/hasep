import axios from 'axios';
import {
  APIResponse,
  DocumentItem,
  ProcessingStatus,
  DocumentReviewData,
  DashboardStats,
  FinancialFormData,
  FinancialRecordItem,
  FinancialKPISummary,
} from '../types';

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Authentication & Google Status
  auth: {
    getStatus: async () => {
      const res = await apiClient.get<APIResponse<{ user: any }>>('/auth/status');
      return res.data.data!;
    },
    getGoogleStatus: async () => {
      const res = await apiClient.get<APIResponse<any>>('/auth/google/status');
      return res.data.data!;
    },
    getGoogleLoginUrl: async () => {
      const res = await apiClient.get<{ authorization_url: string }>('/auth/google/login');
      return res.data.authorization_url;
    },
    disconnectGoogle: async () => {
      const res = await apiClient.delete<APIResponse<boolean>>('/auth/google/disconnect');
      return res.data;
    },
  },

  // Documents
  documents: {
    upload: async (files: File[], autoProcess = true) => {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));
      const res = await apiClient.post<APIResponse<DocumentItem[]>>(
        `/documents/upload?auto_process=${autoProcess}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );
      return res.data.data!;
    },
    list: async (page = 1, limit = 20) => {
      const res = await apiClient.get<{ items: DocumentItem[]; total: number; page: number; limit: number }>(
        `/documents?page=${page}&limit=${limit}`
      );
      return res.data;
    },
    getById: async (id: string) => {
      const res = await apiClient.get<APIResponse<DocumentItem>>(`/documents/${id}`);
      return res.data.data!;
    },
    delete: async (id: string) => {
      const res = await apiClient.delete<APIResponse<boolean>>(`/documents/${id}`);
      return res.data;
    },
    update: async (id: string, payload: { title?: string; document_type?: string }) => {
      const res = await apiClient.put<APIResponse<DocumentItem>>(`/documents/${id}`, payload);
      return res.data.data!;
    },
  },

  // Processing
  processing: {
    trigger: async (id: string) => {
      const res = await apiClient.post<APIResponse<ProcessingStatus>>(`/documents/${id}/process`);
      return res.data.data!;
    },
    getStatus: async (id: string) => {
      const res = await apiClient.get<APIResponse<ProcessingStatus>>(`/documents/${id}/status`);
      return res.data.data!;
    },
    retry: async (id: string) => {
      const res = await apiClient.post<APIResponse<ProcessingStatus>>(`/documents/${id}/retry`);
      return res.data.data!;
    },
  },

  // Review & Approval
  review: {
    getData: async (id: string) => {
      const res = await apiClient.get<APIResponse<DocumentReviewData>>(`/documents/${id}/review`);
      return res.data.data!;
    },
    updateCell: async (documentId: string, payload: { table_id: string; row_id: string; column_id: string; new_value: any; reason?: string }) => {
      const res = await apiClient.put<APIResponse<boolean>>(`/documents/${documentId}/review/cell`, payload);
      return res.data;
    },
    approve: async (id: string, notes?: string) => {
      const res = await apiClient.post<APIResponse<boolean>>(`/documents/${id}/approve`, { notes });
      return res.data;
    },
    reject: async (id: string, reason: string) => {
      const res = await apiClient.post<APIResponse<boolean>>(`/documents/${id}/reject`, { reason });
      return res.data;
    },
  },

  // History & Dashboard Stats
  history: {
    getStats: async () => {
      const res = await apiClient.get<APIResponse<DashboardStats>>('/history/stats');
      return res.data.data!;
    },
  },

  // Project # hasep Dedicated Financial Form API
  financial: {
    getForm: async (documentId: string): Promise<FinancialFormData> => {
      const res = await apiClient.get<APIResponse<FinancialFormData>>(`/documents/${documentId}/form`);
      return res.data.data!;
    },
    updateField: async (documentId: string, fieldPath: string, value: any): Promise<FinancialFormData> => {
      const res = await apiClient.put<APIResponse<FinancialFormData>>(`/documents/${documentId}/form/field`, {
        field_path: fieldPath,
        value,
      });
      return res.data.data!;
    },
    resolveUncertainty: async (documentId: string, fieldPath: string, confirmedValue: any): Promise<FinancialFormData> => {
      const res = await apiClient.post<APIResponse<FinancialFormData>>(`/documents/${documentId}/form/resolve-uncertainty`, {
        field_path: fieldPath,
        confirmed_value: confirmedValue,
      });
      return res.data.data!;
    },
    approve: async (documentId: string, notes?: string, forceOverrideMismatches = false): Promise<any> => {
      const res = await apiClient.post<APIResponse<any>>(`/documents/${documentId}/approve`, {
        notes,
        force_override_mismatches: forceOverrideMismatches,
      });
      return res.data;
    },
    listRecords: async (params?: { start_date?: string; end_date?: string; weekday?: string }): Promise<{ records: FinancialRecordItem[]; kpi_summary: FinancialKPISummary }> => {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.weekday) queryParams.append('weekday', params.weekday);
      const res = await apiClient.get<APIResponse<{ records: FinancialRecordItem[]; kpi_summary: FinancialKPISummary }>>(`/financial-records?${queryParams.toString()}`);
      return res.data.data!;
    },
    getRecordDetail: async (recordId: string): Promise<any> => {
      const res = await apiClient.get<APIResponse<any>>(`/financial-records/${recordId}`);
      return res.data.data!;
    },
  },

  // Google Sheets Integration
  googleSheets: {
    getStatus: async () => {
      const res = await apiClient.get<APIResponse<any>>('/google-sheets/status');
      return res.data.data!;
    },
    connectSpreadsheet: async (spreadsheetId?: string) => {
      const res = await apiClient.post<APIResponse<any>>('/google-sheets/connect-spreadsheet', { spreadsheet_id: spreadsheetId });
      return res.data;
    },
    getSyncJobs: async () => {
      const res = await apiClient.get<APIResponse<any[]>>('/google-sheets/sync-jobs');
      return res.data.data!;
    },
    retryJob: async (jobId: string) => {
      const res = await apiClient.post<APIResponse<any>>(`/google-sheets/sync-jobs/${jobId}/retry`);
      return res.data;
    },
    deleteJob: async (jobId: string) => {
      const res = await apiClient.delete<APIResponse<boolean>>(`/google-sheets/sync-jobs/${jobId}`);
      return res.data;
    },
    retryAllPending: async () => {
      const res = await apiClient.post<APIResponse<any>>('/google-sheets/sync-jobs/retry-pending');
      return res.data;
    },
  },
};
