import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useI18n } from '../i18n/context';
import { api } from '../services/api';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  Eye,
  Trash2,
  ExternalLink,
  RefreshCw,
  FileSpreadsheet,
  FileDown,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { language, t } = useI18n();
  const queryClient = useQueryClient();
  const [editingDocument, setEditingDocument] = React.useState<any>(null);
  const [editTitle, setEditTitle] = React.useState('');
  const [editType, setEditType] = React.useState('');
  const location = useLocation();
  const approvalResult = location.state as {
    approvalCompleted?: boolean;
    googleSync?: { success?: boolean; error?: string; details?: { sheet_url?: string } } | null;
  } | null;

  const { data: stats } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: api.history.getStats,
    refetchInterval: 10000,
  });

  const { data: docsData, isLoading } = useQuery({
    queryKey: ['documentsList'],
    queryFn: () => api.documents.list(1, 20),
    refetchInterval: 8000,
  });

  const deleteMutation = useMutation({
    mutationFn: api.documents.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentsList'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'تعذر حذف المستند. يرجى المحاولة مرة أخرى.';
      window.alert(message);
    },
  });

  const updateDocumentMutation = useMutation({
    mutationFn: () => api.documents.update(editingDocument.id, {
      title: editTitle,
      document_type: editType,
    }),
    onSuccess: () => {
      setEditingDocument(null);
      queryClient.invalidateQueries({ queryKey: ['documentsList'] });
    },
    onError: (error: any) => {
      window.alert(error?.response?.data?.detail || 'تعذر تحديث بيانات المستند.');
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ready_for_review':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">جاهز للمراجعة</span>;
      case 'approved':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">معتمد ومزامن إلى Google Sheets</span>;
      case 'exported':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">تم التصدير بنجاح</span>;
      case 'processing':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">قيد المعالجة...</span>;
      case 'failed':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">فشلت العملية</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">{status}</span>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{t('dashboard')}</h2>
          <p className="text-sm text-slate-500">
            {language === 'ar' ? 'متابعة المستندات وعمليات الاستخراج والمزامنة التلقائية مع Google Sheets' : 'Track document extraction and automatic Google Sheets sync'}
          </p>
        </div>
        <Link
          to="/upload"
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm shadow-sm transition"
        >
          <UploadCloud className="w-4 h-4" />
          <span>{t('upload')}</span>
        </Link>
      </div>

      {approvalResult?.approvalCompleted && (
        <div className={`rounded-xl border p-4 text-sm ${
          approvalResult.googleSync?.success
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border-amber-200 bg-amber-50 text-amber-800'
        }`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>
              تم اعتماد وقفل النموذج والعودة إلى لوحة التحكم.
              {approvalResult.googleSync?.success
                ? ' تمت مزامنته مع Google Sheets بنجاح.'
                : ` حالة المزامنة: ${approvalResult.googleSync?.error || 'بانتظار الإعداد أو إعادة المحاولة.'}`}
            </span>
            {approvalResult.googleSync?.details?.sheet_url && (
              <a
                href={approvalResult.googleSync.details.sheet_url}
                target="_blank"
                rel="noreferrer"
                className="font-bold underline"
              >
                فتح Google Sheets
              </a>
            )}
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">{t('totalDocuments')}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{stats?.total_documents ?? 0}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center">
            <FileText className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">{t('pendingReviews')}</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{stats?.pending_reviews ?? 0}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">{t('successfulExports')}</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{stats?.successful_exports ?? 0}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500">{t('failedOperations')}</p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{stats?.failed_operations ?? 0}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-base">
            {language === 'ar' ? 'أحدث المستندات المرفوعة' : 'Recent Uploaded Documents'}
          </h3>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['documentsList'] })}
            className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 transition"
            title="تحديث القائمة"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-slate-500 text-sm">جاري التحميل...</div>
        ) : !docsData?.items?.length ? (
          <div className="p-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-slate-600 font-medium">لم يتم رفع أي مستندات حتى الآن.</p>
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{t('upload')}</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-right">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">المستند</th>
                  <th className="py-3 px-4">نوع المستند</th>
                  <th className="py-3 px-4">الحالة</th>
                  <th className="py-3 px-4">تاريخ الرفع</th>
                  <th className="py-3 px-4 text-center">الإجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docsData.items.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded bg-slate-100 border border-slate-200 overflow-hidden flex-shrink-0">
                          {doc.pages?.[0]?.preview_url ? (
                            <img
                              src={doc.pages[0].preview_url}
                              alt={doc.title}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <FileText className="w-5 h-5 text-slate-400 m-2.5" />
                          )}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 leading-snug">{doc.title}</p>
                          <p className="text-xs text-slate-400">{(doc.file_size / 1024).toFixed(1)} KB • {doc.original_filename}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {doc.document_type || 'مستند عام'}
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-500 font-sans">
                      {new Date(doc.created_at).toLocaleString('ar-EG')}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {doc.status === 'processing' ? (
                          <Link
                            to={`/processing/${doc.id}`}
                            className="p-1.5 rounded bg-amber-50 hover:bg-amber-100 text-amber-700 transition"
                            title="متابعة المعالجة"
                          >
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          </Link>
                        ) : (
                          <Link
                            to={`/review/${doc.id}`}
                            className="p-1.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 transition"
                            title="مراجعة وتعديل البيانات"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>
                        )}

                        {doc.status === 'approved' && (
                          <a
                            href={`/api/v1/documents/${doc.id}/pdf`}
                            download
                            className="p-1.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 transition"
                            title="تحميل تقرير PDF"
                          >
                            <FileDown className="w-4 h-4" />
                          </a>
                        )}

                        <button
                          type="button"
                          onClick={() => {
                            if (confirm('هل أنت متأكد من حذف هذا المستند وجميع بياناته؟')) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          className="p-1.5 rounded hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition disabled:cursor-not-allowed disabled:opacity-50"
                          title="حذف المستند"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingDocument(doc);
                            setEditTitle(doc.title);
                            setEditType(doc.document_type || 'other');
                          }}
                          className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                          title="تعديل بيانات المستند"
                        >
                          تعديل
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editingDocument && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl" dir="rtl">
            <h3 className="text-lg font-bold text-slate-900">تعديل بيانات المستند</h3>
            <p className="mt-1 text-xs text-slate-500">
              تاريخ المستند: اليوم فقط ولا يمكن تغييره إلى تاريخ آخر.
            </p>
            <label className="mt-5 block text-xs font-semibold text-slate-700">اسم المستند</label>
            <input
              value={editTitle}
              onChange={(event) => setEditTitle(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <label className="mt-4 block text-xs font-semibold text-slate-700">نوع المستند</label>
            <input
              value={editType}
              onChange={(event) => setEditType(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingDocument(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={() => updateDocumentMutation.mutate()}
                disabled={updateDocumentMutation.isPending}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
              >
                {updateDocumentMutation.isPending ? 'جاري الحفظ...' : 'حفظ التعديل'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
