import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useI18n } from '../i18n/context';
import { api } from '../services/api';
import {
  Settings as SettingsIcon,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Key,
  ExternalLink,
  Table,
  RefreshCw,
  AlertTriangle,
  Clock,
  FileSpreadsheet,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { language, setLanguage, t } = useI18n();
  const queryClient = useQueryClient();
  const [spreadsheetInput, setSpreadsheetInput] = useState('');


  // Google OAuth Status
  const { data: googleAuth, refetch: refetchGoogleAuth } = useQuery({
    queryKey: ['googleAuthStatus'],
    queryFn: api.auth.getGoogleStatus,
  });

  // Google Sheets & Sync Status
  const { data: googleSheets, refetch: refetchGoogleSheets } = useQuery({
    queryKey: ['googleSheetsStatus'],
    queryFn: api.googleSheets.getStatus,
  });

  // Google Sheets Sync Jobs
  const { data: syncJobs, refetch: refetchSyncJobs } = useQuery({
    queryKey: ['googleSyncJobs'],
    queryFn: api.googleSheets.getSyncJobs,
  });

  const disconnectGoogleMutation = useMutation({
    mutationFn: api.auth.disconnectGoogle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['googleAuthStatus'] });
      queryClient.invalidateQueries({ queryKey: ['googleSheetsStatus'] });
      alert('تم فصل حساب Google بنجاح.');
    },
  });

  const connectSpreadsheetMutation = useMutation({
    mutationFn: (sheetId?: string) => api.googleSheets.connectSpreadsheet(sheetId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['googleSheetsStatus'] });
      alert(data.message || 'تم ربط ملف Google Sheets بنجاح.');
      setSpreadsheetInput('');
    },
    onError: (err: any) => {
      alert(`خطأ: ${err?.response?.data?.detail || err.message}`);
    },
  });

  const retryJobMutation = useMutation({
    mutationFn: (jobId: string) => api.googleSheets.retryJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['googleSheetsStatus'] });
      queryClient.invalidateQueries({ queryKey: ['googleSyncJobs'] });
      alert('تمت إعادة إرسال المهمة بنجاح.');
    },
    onError: (err: any) => {
      alert(`فشلت إعادة المحاولة: ${err?.response?.data?.detail || err.message}`);
    },
  });

  const retryAllMutation = useMutation({
    mutationFn: () => api.googleSheets.retryAllPending(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['googleSheetsStatus'] });
      queryClient.invalidateQueries({ queryKey: ['googleSyncJobs'] });
      alert(data.message || 'تمت إعادة محاولة جميع المهمات.');
    },
    onError: (err: any) => {
      alert(`خطأ: ${err?.response?.data?.detail || err.message}`);
    },
  });

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: string) => api.googleSheets.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['googleSyncJobs'] });
      queryClient.invalidateQueries({ queryKey: ['googleSheetsStatus'] });
    },
    onError: (err: any) => {
      alert(`تعذر حذف المهمة: ${err?.response?.data?.detail || err.message}`);
    },
  });

  const isGoogleConnected = googleAuth?.is_connected;
  const syncStats = googleSheets?.sync_stats;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">{t('settings')}</h2>
        <p className="text-sm text-slate-500">
          {language === 'ar'
            ? 'إدارة التكاملات، حالة الخدمات الخارجية، وتفضيلات النظام'
            : 'Manage integrations, external services status, and system settings'}
        </p>
      </div>

      {/* Google Sheets Integration Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Google Sheets Integration</h3>
              <p className="text-xs text-slate-500">
                المزامنة التلقائية الدورية لنماذج مطعم زنجر Up بعد الاعتماد النهائي فقط
              </p>
            </div>
          </div>
          {isGoogleConnected ? (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>متصل</span>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
              <XCircle className="w-3.5 h-3.5 text-amber-500" />
              <span>غير متصل</span>
            </span>
          )}
        </div>

        {isGoogleConnected ? (
          <div className="space-y-5 text-xs">
            {/* Account Details Box */}
            <div className="p-4 bg-slate-50 rounded-xl space-y-2 border border-slate-100">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-slate-500">البريد الإلكتروني المرتبط:</p>
                  <p className="font-bold text-slate-900 text-sm">{googleAuth?.email}</p>
                </div>
                <div>
                  <p className="text-slate-500">صلاحية الاتصال:</p>
                  <p className="font-semibold text-emerald-700">
                    {googleAuth?.is_expired ? 'منتهي الصلاحية (بحاجة لتجديد)' : 'نشط وساري الصلاحية'}
                  </p>
                </div>
                <button
                  onClick={() => disconnectGoogleMutation.mutate()}
                  disabled={disconnectGoogleMutation.isPending}
                  className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 font-semibold transition"
                >
                  فصل حساب Google
                </button>
              </div>
            </div>

            {/* Target Google Spreadsheet */}
            <div className="p-4 bg-emerald-50/50 rounded-xl space-y-3 border border-emerald-100">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-emerald-950 text-sm">ملف Google Sheets المستهدف</h4>
                  <p className="text-emerald-700 text-[11px]">
                    تُنشأ ورقة يومية باسم التاريخ (YYYY-MM-DD) داخل هذا الملف
                  </p>
                </div>
                {googleSheets?.spreadsheet_url && (
                  <a
                    href={googleSheets.spreadsheet_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-emerald-700 hover:text-emerald-900 font-bold underline"
                  >
                    <span>فتح جدول البيانات في Google Sheets</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              {googleSheets?.spreadsheet_id ? (
                <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-emerald-200">
                  <div className="font-mono text-slate-700 text-xs truncate max-w-md">
                    المعرف: <span className="font-bold">{googleSheets.spreadsheet_id}</span>
                  </div>
                  <span className="text-emerald-600 font-semibold text-[11px]">جاهز للاستقبال</span>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="أدخل Spreadsheet ID يدويًا أو اتركه فارغًا للإنشاء التلقائي"
                    value={spreadsheetInput}
                    onChange={(e) => setSpreadsheetInput(e.target.value)}
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                  <button
                    onClick={() => connectSpreadsheetMutation.mutate(spreadsheetInput || undefined)}
                    disabled={connectSpreadsheetMutation.isPending}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 transition"
                  >
                    {spreadsheetInput ? 'ربط الملف' : 'إنشاء ملف # hasep جديد'}
                  </button>
                </div>
              )}
            </div>

            {/* Sync Queue Statistics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <p className="text-slate-500 text-[11px]">إجمالي المهمات</p>
                <p className="text-lg font-bold text-slate-800">{syncStats?.total_jobs || 0}</p>
              </div>
              <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                <p className="text-emerald-700 text-[11px]">مكتملة بنجاح</p>
                <p className="text-lg font-bold text-emerald-800">{syncStats?.success_count || 0}</p>
              </div>
              <div className="bg-amber-50 p-3 rounded-lg border border-amber-200">
                <p className="text-amber-700 text-[11px]">بانتظار المزامنة</p>
                <p className="text-lg font-bold text-amber-800">{syncStats?.pending_count || 0}</p>
              </div>
              <div className="bg-rose-50 p-3 rounded-lg border border-rose-200">
                <p className="text-rose-700 text-[11px]">فشلت المزامنة</p>
                <p className="text-lg font-bold text-rose-800">{syncStats?.failed_count || 0}</p>
              </div>
            </div>

            {/* Sync Status Banner & Actions */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-slate-500 text-[11px]">
                آخر مزامنة ناجحة: <span className="font-semibold text-slate-800">{syncStats?.last_synced_at ? new Date(syncStats.last_synced_at).toLocaleString('ar-JO') : 'لا يوجد سجل مزامنة بعد'}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    refetchGoogleSheets();
                    refetchSyncJobs();
                  }}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1 font-semibold"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>تحديث الحالة</span>
                </button>
                {(syncStats?.pending_count > 0 || syncStats?.failed_count > 0) && (
                  <button
                    onClick={() => retryAllMutation.mutate()}
                    disabled={retryAllMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-1 font-semibold shadow-sm"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>إعادة محاولة المعلق والفاشل</span>
                  </button>
                )}
              </div>
            </div>

            {/* Sync Jobs Table */}
            {syncJobs && syncJobs.length > 0 && (
              <div className="space-y-2 pt-2">
                <h5 className="font-bold text-slate-800 text-xs">سجل مهمات المزامنة الأخيرة</h5>
                <div className="border border-slate-200 rounded-lg overflow-hidden overflow-x-auto">
                  <table className="w-full text-right text-[11px]">
                    <thead className="bg-slate-100 text-slate-600 border-b border-slate-200">
                      <tr>
                        <th className="p-2">معرف السجل المعتمد</th>
                        <th className="p-2">ورقة اليوم</th>
                        <th className="p-2">الحالة</th>
                        <th className="p-2">المحاولات</th>
                        <th className="p-2">تاريخ المزامنة</th>
                        <th className="p-2">السبب / الخطأ</th>
                        <th className="p-2 text-center">إجراء</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {syncJobs.map((job: any) => (
                        <tr key={job.id} className="hover:bg-slate-50">
                          <td className="p-2 font-mono text-slate-700">{job.approved_record_id.slice(0, 8)}...</td>
                          <td className="p-2 font-bold text-slate-800">{job.target_sheet_name || '-'}</td>
                          <td className="p-2">
                            {job.status === 'SUCCESS' && (
                              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold text-[10px]">
                                ناجحة
                              </span>
                            )}
                            {job.status === 'PENDING' && (
                              <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold text-[10px]">
                                قيد الانتظار
                              </span>
                            )}
                            {job.status === 'PROCESSING' && (
                              <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold text-[10px]">
                                جاري المعالجة
                              </span>
                            )}
                            {job.status === 'RETRY' && (
                              <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 font-semibold text-[10px]">
                                إعادة محاولة
                              </span>
                            )}
                            {job.status === 'FAILED' && (
                              <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-semibold text-[10px]">
                                فشلت
                              </span>
                            )}
                          </td>
                          <td className="p-2 text-center">{job.retry_count} / {job.max_retries}</td>
                          <td className="p-2 text-slate-500">
                            {job.synced_at ? new Date(job.synced_at).toLocaleTimeString('ar-JO') : '-'}
                          </td>
                          <td className="p-2 text-rose-600 max-w-xs truncate" title={job.last_error}>
                            {job.last_error || '-'}
                          </td>
                          <td className="p-2 text-center">
                            <div className="flex items-center justify-center gap-1">
                            {job.status !== 'SUCCESS' && (
                              <button
                                onClick={() => retryJobMutation.mutate(job.id)}
                                disabled={retryJobMutation.isPending}
                                className="px-2 py-1 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-semibold transition"
                              >
                                إعادة
                              </button>
                            )}
                            <button
                              onClick={() => {
                                if (confirm('هل أنت متأكد من حذف مهمة المزامنة؟')) {
                                  deleteJobMutation.mutate(job.id);
                                }
                              }}
                              disabled={deleteJobMutation.isPending}
                              className="px-2 py-1 bg-rose-50 hover:bg-rose-100 rounded text-rose-700 font-semibold transition disabled:opacity-50"
                            >
                              حذف
                            </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3 text-xs">
            <p className="text-slate-600 leading-relaxed">
              قم بربط حساب Google الخاص بك لتمكين الحفظ التلقائي للنماذج المالية المعتمدة في Google Sheets.
              يتم تصدير كل نموذج معتمد داخل ورقة يومية مستقلة باسم التاريخ (مثل 2026-11-14)
              مع الحفاظ الكامل على معادلات المجاميع وحسابات الصندوق والمبيعات.
            </p>
            <button
              onClick={async () => {
                const url = await api.auth.getGoogleLoginUrl();
                window.location.href = url;
              }}
              className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition flex items-center gap-2 shadow-sm"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>ربط حساب Google (Connect Google Account)</span>
            </button>
          </div>
        )}
      </div>

      {/* AI Services Status */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <Key className="w-4 h-4 text-emerald-600" />
          <span>حالة موفري الذكاء الاصطناعي و OCR</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800">Google Gemini API</span>
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                محرك الذكاء الاصطناعي الحصري
              </span>
            </div>
            <p className="text-slate-500">
              نموذج `gemini-3.5-flash-lite` للتعرف البصري واستخراج البيانات المنظمة من النماذج المالية الورقية.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800">Deterministic Financial Engine</span>
              <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] font-semibold">
                محرك الحسابات المحلي
              </span>
            </div>
            <p className="text-slate-500">
              8 معادلات مالية حتمية بدقة Decimal لمنع الأخطاء الحسابية وتطابق مخرجات Excel و Google Sheets.
            </p>
          </div>
        </div>
      </div>

      {/* Language Preferences */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm">تفضيلات واجهة الاستخدام</h3>
        <div className="flex items-center gap-4 text-xs">
          <button
            onClick={() => setLanguage('ar')}
            className={`px-4 py-2 rounded-lg font-bold transition border ${
              language === 'ar'
                ? 'bg-emerald-600 text-white border-emerald-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            العربية (RTL افتراضي)
          </button>
          <button
            onClick={() => setLanguage('en')}
            className={`px-4 py-2 rounded-lg font-bold transition border ${
              language === 'en'
                ? 'bg-emerald-600 text-white border-emerald-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
            }`}
          >
            English (LTR)
          </button>
        </div>
      </div>
    </div>
  );
};
