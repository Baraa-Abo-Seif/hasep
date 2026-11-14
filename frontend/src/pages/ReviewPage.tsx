import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useI18n } from '../i18n/context';
import { api } from '../services/api';
import {
  FileCheck,
  FileDown,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Check,
  Calendar,
  Lock,
  FileSpreadsheet,
  ExternalLink,
} from 'lucide-react';
import { FinancialFormData } from '../types';

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [approvalNotes, setApprovalNotes] = useState('');
  const [forceOverride, setForceOverride] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [approvalSuccess, setApprovalSuccess] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [tempValue, setTempValue] = useState<string>('');

  const { data: formData, isLoading, isError } = useQuery<FinancialFormData>({
    queryKey: ['financialForm', id],
    queryFn: () => api.financial.getForm(id!),
    enabled: !!id,
  });

  const updateFieldMutation = useMutation({
    mutationFn: ({ path, value }: { path: string; value: any }) =>
      api.financial.updateField(id!, path, value),
    onSuccess: (updatedForm) => {
      queryClient.setQueryData(['financialForm', id], updatedForm);
      setEditingPath(null);
    },
  });

  const [syncResult, setSyncResult] = useState<any>(null);

  const approveMutation = useMutation({
    mutationFn: () => api.financial.approve(id!, approvalNotes, forceOverride),
    onSuccess: (res: any) => {
      setApprovalError(null);
      setShowApprovalModal(false);
      setApprovalSuccess(true);
      if (res?.data?.google_sync) {
        setSyncResult(res.data.google_sync);
      }
      queryClient.invalidateQueries({ queryKey: ['financialForm', id] });
      navigate('/dashboard', {
        replace: true,
        state: {
          approvalCompleted: true,
          googleSync: res?.data?.google_sync ?? null,
        },
      });
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'تعذر اعتماد النموذج. يرجى المحاولة مرة أخرى.';
      setApprovalError(message);
    },
  });

  const handleCellBlur = (path: string, originalVal: any) => {
    if (tempValue !== undefined && tempValue !== String(originalVal ?? '')) {
      updateFieldMutation.mutate({ path, value: tempValue });
    } else {
      setEditingPath(null);
    }
  };

  const getCellVal = (path: string, currentVal: any) => {
    if (editingPath === path) return tempValue;
    if (currentVal === null || currentVal === undefined || currentVal === '0.00' || currentVal === 0) {
      return '';
    }
    return String(currentVal);
  };

  if (isLoading) {
    return (
      <div className="flex h-96 flex-col items-center justify-center space-y-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-transparent" />
        <p className="text-sm font-medium text-slate-600">جاري تحميل النموذج الرقمي المطابق للورقة...</p>
      </div>
    );
  }

  if (isError || !formData) {
    return (
      <div className="mx-auto max-w-xl rounded-xl border border-red-200 bg-red-50 p-8 text-center text-red-700">
        <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-red-500" />
        <h2 className="text-lg font-bold">تعذر تحميل بيانات النموذج</h2>
        <Link to="/dashboard" className="mt-4 inline-block rounded-lg bg-red-600 px-4 py-2 text-white">
          العودة للوحة التحكم
        </Link>
      </div>
    );
  }

  // Ensure 10 rows
  const attendanceRows = [...formData.attendance];
  while (attendanceRows.length < 10) {
    attendanceRows.push({ employee_name: '', status: 'حاضر', duration_hours: '0.00' });
  }

  const purchasesRows = [...formData.purchases];
  while (purchasesRows.length < 10) {
    purchasesRows.push({ item: '', amount: '0.00' });
  }

  const expensesRows = [...formData.expenses];
  while (expensesRows.length < 10) {
    expensesRows.push({ item: '', amount: '0.00' });
  }

  // Date parsing
  const dateParts = (formData.form_date || '2026-11-13').split('-');
  const dateDay = dateParts[2] || '31';
  const dateMonth = dateParts[1] || '11';
  const dateYear = dateParts[0] || '2026';

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-24 font-sans" dir="rtl">
      {/* Control Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            <ArrowRight className="h-4 w-4" />
            لوحة التحكم
          </Link>
          <span className="text-xs text-slate-500">
            الحالة:{' '}
            <strong className="rounded bg-slate-100 px-2 py-0.5 text-slate-800">
              نموذج يوم {formData.day_of_week} ({formData.form_date})
            </strong>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={`/api/v1/documents/${id}/pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
          >
            <FileDown className="h-4 w-4" />
            تحميل تقرير PDF بنفس الستايل
          </a>
          <button
            onClick={() => setShowApprovalModal(true)}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700"
          >
            <ShieldCheck className="h-4 w-4" />
            الاعتماد النهائي للنموذج
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {approvalSuccess && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-5 text-emerald-900 shadow-sm space-y-3">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 flex-shrink-0" />
            <div>
              <h3 className="text-base font-bold">تم اعتماد وقفل النموذج بنجاح والمزامنة التلقائية</h3>
              <p className="text-xs text-emerald-700">
                تم حفظ البيانات محلياً، حذف الصور المؤقتة من الخادم وفق المعايير الأمنية، وإنشاء تقرير PDF المطابق لستايل الورقة الأصلية.
              </p>
            </div>
          </div>

          {/* Google Sheets Sync Result */}
          {syncResult?.details?.sheet_url ? (
            <div className="p-3 bg-white rounded-lg border border-emerald-200 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                <span className="font-semibold text-slate-800">
                  تمت المزامنة بنجاح إلى ورقة Google Sheets الشهرية ({syncResult.details.sheet_name || formData.form_date.slice(0, 7)})
                </span>
              </div>
              <a
                href={syncResult.details.sheet_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-xs hover:bg-emerald-700 transition"
              >
                <span>فتح الورقة في Google Sheets</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          ) : syncResult?.error ? (
            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
              <span>تنبيه المزامنة السحابية: {syncResult.error} (يمكن إعادة المحاولة لاحقاً من صفحة الإعدادات).</span>
              <Link to="/settings" className="font-bold underline text-amber-900">
                الإعدادات
              </Link>
            </div>
          ) : null}

          <div className="flex gap-3 pt-1">
            <a
              href={`/api/v1/documents/${id}/pdf`}
              download
              className="flex items-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
            >
              <FileDown className="h-4 w-4" />
              تحميل التقرير النهائي المعتمد (PDF)
            </a>
          </div>
        </div>
      )}

      {/* Mismatches Banner */}
      {formData.calculation_mismatches.length > 0 && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-xs text-red-900 shadow-sm">
          <div className="flex items-center gap-2 font-bold">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <span>تنبيه فروقات حسابية في الورقة ({formData.calculation_mismatches.length}):</span>
          </div>
          <div className="mt-2 space-y-1">
            {formData.calculation_mismatches.map((m, idx) => (
              <div key={idx} className="flex justify-between border-t border-red-200 pt-1">
                <span>{m.message}</span>
                <span className="font-mono font-bold">الفارق: {m.difference} د.أ</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* THE PHYSICAL PAPER REPLICA SHEET CONTAINER                                */}
      {/* ========================================================================= */}
      <div className="mx-auto w-full max-w-[850px] rounded-lg border-2 border-slate-300 bg-white p-8 shadow-xl transition-all">
        {/* Paper Header */}
        <div className="flex items-start justify-between border-b border-transparent pb-3">
          {/* Right Header: مطعم زنجر Up */}
          <div className="text-right">
            <h2 className="text-base font-bold tracking-tight text-black">مطعم زنجر Up</h2>
          </div>

          {/* Center Header: ZingérUP Logo */}
          <div className="text-center">
            <div className="text-2xl font-black tracking-tight text-slate-900" style={{ fontFamily: 'sans-serif' }}>
              Zingé<span className="italic">R</span>UP
            </div>
            <div className="text-[10px] italic tracking-wider text-slate-600">Zinger World</div>
          </div>

          {/* Left Header: Phone - Mall */}
          <div className="text-left font-sans text-xs font-bold text-black" dir="ltr">
            0795235333 - Taj Mall
          </div>
        </div>

        {/* Date and Day Row */}
        <div className="mt-3 flex items-center justify-between px-2 text-xs font-bold text-black">
          {/* Left: DATE */}
          <div className="flex items-center gap-1 font-sans" dir="ltr">
            <span className="font-bold">DATE:</span>
            <input
              type="text"
              value={getCellVal('form_date_day', dateDay)}
              onFocus={() => {
                setEditingPath('form_date_day');
                setTempValue(dateDay);
              }}
              onChange={(e) => setTempValue(e.target.value)}
              onBlur={() => {
                const newD = tempValue.padStart(2, '0');
                updateFieldMutation.mutate({ path: 'form_date', value: `${dateYear}-${dateMonth}-${newD}` });
              }}
              className="w-8 border-b border-black text-center font-bold focus:bg-amber-50 focus:outline-none"
            />
            <span>/</span>
            <input
              type="text"
              value={getCellVal('form_date_month', dateMonth)}
              onFocus={() => {
                setEditingPath('form_date_month');
                setTempValue(dateMonth);
              }}
              onChange={(e) => setTempValue(e.target.value)}
              onBlur={() => {
                const newM = tempValue.padStart(2, '0');
                updateFieldMutation.mutate({ path: 'form_date', value: `${dateYear}-${newM}-${dateDay}` });
              }}
              className="w-8 border-b border-black text-center font-bold focus:bg-amber-50 focus:outline-none"
            />
            <span>/</span>
            <span className="w-12 border-b border-black text-center">{dateYear}</span>
          </div>

          {/* Right: DAY */}
          <div className="flex items-center gap-2">
            <span>DAY:</span>
            <span className="min-w-[120px] border-b border-black px-2 pb-0.5 text-center font-semibold text-slate-800">
              {formData.day_of_week}
            </span>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* 1. TOP 5-COLUMN TABLE (المصاريف | المشتريات | الموظف | دخول | خروج)       */}
        {/* ========================================================================= */}
        <div className="mt-4 border-2 border-black">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b-2 border-black bg-slate-50 text-center font-bold text-black">
                <th className="w-[18%] border-l-2 border-black py-2.5">المصاريف</th>
                <th className="w-[18%] border-l-2 border-black py-2.5">المشتريات</th>
                <th className="w-[30%] border-l-2 border-black py-2.5">الموظف</th>
                <th className="w-[14%] border-l-2 border-black py-2.5">دخول</th>
                <th className="w-[14%] border-l-2 border-black py-2.5">خروج</th>
                <th className="w-[10%] py-2.5">ساعات العمل</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 10 }).map((_, idx) => {
                const exp = expensesRows[idx];
                const pur = purchasesRows[idx];
                const att = attendanceRows[idx];

                return (
                  <tr key={idx} className="border-b border-black text-center">
                    {/* 1. المصاريف (Expenses) */}
                    <td className="border-l-2 border-black p-0">
                      <input
                        type="text"
                        value={getCellVal(`expenses.${idx}.amount`, exp?.amount)}
                        onFocus={() => {
                          setEditingPath(`expenses.${idx}.amount`);
                          setTempValue(exp?.amount ? String(exp.amount) : '');
                        }}
                        onChange={(e) => setTempValue(e.target.value)}
                        onBlur={() => handleCellBlur(`expenses.${idx}.amount`, exp?.amount)}
                        className="h-8 w-full text-center font-mono text-sm font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                      />
                    </td>

                    {/* 2. المشتريات (Purchases) */}
                    <td className="border-l-2 border-black p-0">
                      <input
                        type="text"
                        value={getCellVal(`purchases.${idx}.amount`, pur?.amount)}
                        onFocus={() => {
                          setEditingPath(`purchases.${idx}.amount`);
                          setTempValue(pur?.amount ? String(pur.amount) : '');
                        }}
                        onChange={(e) => setTempValue(e.target.value)}
                        onBlur={() => handleCellBlur(`purchases.${idx}.amount`, pur?.amount)}
                        className="h-8 w-full text-center font-mono text-sm font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                      />
                    </td>

                    {/* 3. الموظف (Employee Name) */}
                    <td className="border-l-2 border-black p-0">
                      <input
                        type="text"
                        value={getCellVal(`attendance.${idx}.employee_name`, att?.employee_name)}
                        onFocus={() => {
                          setEditingPath(`attendance.${idx}.employee_name`);
                          setTempValue(att?.employee_name || '');
                        }}
                        onChange={(e) => setTempValue(e.target.value)}
                        onBlur={() => handleCellBlur(`attendance.${idx}.employee_name`, att?.employee_name)}
                        className="h-8 w-full px-2 text-center text-xs font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                      />
                    </td>

                    {/* 4. دخول (Entry time) */}
                    <td className="border-l-2 border-black p-0">
                      <input
                        type="text"
                        value={getCellVal(`attendance.${idx}.entry_time`, att?.entry_time)}
                        onFocus={() => {
                          setEditingPath(`attendance.${idx}.entry_time`);
                          setTempValue(att?.entry_time || '');
                        }}
                        onChange={(e) => setTempValue(e.target.value)}
                        onBlur={() => handleCellBlur(`attendance.${idx}.entry_time`, att?.entry_time)}
                        className="h-8 w-full text-center font-mono text-xs text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                      />
                    </td>

                    {/* 5. خروج (Exit time) */}
                    <td className="border-l-2 border-black p-0">
                      <input
                        type="text"
                        value={getCellVal(`attendance.${idx}.exit_time`, att?.exit_time)}
                        onFocus={() => {
                          setEditingPath(`attendance.${idx}.exit_time`);
                          setTempValue(att?.exit_time || '');
                        }}
                        onChange={(e) => setTempValue(e.target.value)}
                        onBlur={() => handleCellBlur(`attendance.${idx}.exit_time`, att?.exit_time)}
                        className="h-8 w-full text-center font-mono text-xs text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                      />
                    </td>
                    <td className="p-0">
                      <input
                        type="text"
                        value={String(att?.duration_hours ?? '0.00')}
                        readOnly
                        title="تحسب تلقائياً من وقت الدخول والخروج"
                        className="h-8 w-full bg-slate-50 text-center font-mono text-xs font-bold text-black"
                      />
                    </td>
                  </tr>
                );
              })}

              {/* ========================================================================= */}
              {/* 2. SUBTOTALS ROW (المجموع الكلي للمصاريف / المشتريات / كلاهما)               */}
              {/* ========================================================================= */}
              <tr className="border-t-2 border-black">
                {/* Under المصاريف: المجموع الكلي */}
                <td className="border-l-2 border-black p-1 text-center align-top">
                  <div className="text-[10px] font-bold text-black">المجموع الكلي:</div>
                  <input
                    type="text"
                    value={getCellVal('summary.total_expenses', formData.summary.total_expenses)}
                    onFocus={() => {
                      setEditingPath('summary.total_expenses');
                      setTempValue(String(formData.summary.total_expenses));
                    }}
                    onChange={(e) => setTempValue(e.target.value)}
                    onBlur={() => handleCellBlur('summary.total_expenses', formData.summary.total_expenses)}
                    className="mt-0.5 w-full text-center font-mono text-sm font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                  />
                </td>

                {/* Under المشتريات: المجموع الكلي */}
                <td className="border-l-2 border-black p-1 text-center align-top">
                  <div className="text-[10px] font-bold text-black">المجموع الكلي:</div>
                  <input
                    type="text"
                    value={getCellVal('summary.total_purchases', formData.summary.total_purchases)}
                    onFocus={() => {
                      setEditingPath('summary.total_purchases');
                      setTempValue(String(formData.summary.total_purchases));
                    }}
                    onChange={(e) => setTempValue(e.target.value)}
                    onBlur={() => handleCellBlur('summary.total_purchases', formData.summary.total_purchases)}
                    className="mt-0.5 w-full text-center font-mono text-sm font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                  />
                </td>

                {/* Under الموظف + دخول + خروج: مجموع المصاريف والمشتريات */}
                <td colSpan={3} className="p-1 text-center align-top">
                  <div className="text-right text-[10px] font-bold text-black pr-2">
                    مجموع المصاريف والمشتريات:
                  </div>
                  <input
                    type="text"
                    value={getCellVal(
                      'summary.total_expenses_and_purchases',
                      formData.summary.total_expenses_and_purchases
                    )}
                    onFocus={() => {
                      setEditingPath('summary.total_expenses_and_purchases');
                      setTempValue(String(formData.summary.total_expenses_and_purchases));
                    }}
                    onChange={(e) => setTempValue(e.target.value)}
                    onBlur={() =>
                      handleCellBlur(
                        'summary.total_expenses_and_purchases',
                        formData.summary.total_expenses_and_purchases
                      )
                    }
                    className="mt-0.5 w-full text-center font-mono text-base font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                  />
                </td>
              </tr>
            </tbody>
          </table>

          {/* ========================================================================= */}
          {/* 3. 4-COLUMN APPS & CARDS ROW (الفيزا | طلبات | كريم | أشيائي)              */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-4 border-t-2 border-black text-xs">
            {/* Box 1 (Right): الفيزا */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">الفيزا:</div>
              <input
                type="text"
                value={getCellVal('sales.visa', formData.sales.visa)}
                onFocus={() => {
                  setEditingPath('sales.visa');
                  setTempValue(String(formData.sales.visa));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.visa', formData.sales.visa)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 2: طلبات */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">طلبات:</div>
              <input
                type="text"
                value={getCellVal('sales.orders', formData.sales.orders)}
                onFocus={() => {
                  setEditingPath('sales.orders');
                  setTempValue(String(formData.sales.orders));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.orders', formData.sales.orders)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 3: كريم */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">كريم:</div>
              <input
                type="text"
                value={getCellVal('sales.kareem', formData.sales.kareem)}
                onFocus={() => {
                  setEditingPath('sales.kareem');
                  setTempValue(String(formData.sales.kareem));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.kareem', formData.sales.kareem)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 4 (Left): أشيائي */}
            <div className="p-1">
              <div className="text-[10px] font-bold text-black">أشيائي:</div>
              <input
                type="text"
                value={getCellVal('sales.ashaayi', formData.sales.ashaayi)}
                onFocus={() => {
                  setEditingPath('sales.ashaayi');
                  setTempValue(String(formData.sales.ashaayi));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.ashaayi', formData.sales.ashaayi)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 4. 4-COLUMN CASH RECONCILIATION ROW (الرصيد السابق | الرصيد الحالي | زيادة | نقص) */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-4 border-t-2 border-black text-xs">
            {/* Box 1 (Right): الرصيد السابق */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">الرصيد السابق:-</div>
              <input
                type="text"
                value={getCellVal('summary.previous_balance', formData.summary.previous_balance)}
                onFocus={() => {
                  setEditingPath('summary.previous_balance');
                  setTempValue(String(formData.summary.previous_balance));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('summary.previous_balance', formData.summary.previous_balance)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 2: الرصيد الحالي */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">الرصيد الحالي:-</div>
              <input
                type="text"
                value={getCellVal(
                  'summary.handwritten_current_balance',
                  formData.summary.handwritten_current_balance ?? formData.summary.current_balance
                )}
                onFocus={() => {
                  setEditingPath('summary.handwritten_current_balance');
                  setTempValue(
                    String(
                      formData.summary.handwritten_current_balance ?? formData.summary.current_balance
                    )
                  );
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() =>
                  handleCellBlur('summary.handwritten_current_balance', formData.summary.handwritten_current_balance)
                }
                className="mt-0.5 w-full text-center font-mono text-sm font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 3: زيادة */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">زيادة</div>
              <input
                type="text"
                value={getCellVal('summary.increase', formData.summary.increase)}
                onFocus={() => {
                  setEditingPath('summary.increase');
                  setTempValue(String(formData.summary.increase));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('summary.increase', formData.summary.increase)}
                className="mt-0.5 w-full text-center font-mono text-sm font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 4 (Left): نقص */}
            <div className="p-1">
              <div className="text-[10px] font-bold text-black">نقص</div>
              <input
                type="text"
                value={getCellVal('summary.decrease', formData.summary.decrease)}
                onFocus={() => {
                  setEditingPath('summary.decrease');
                  setTempValue(String(formData.summary.decrease));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('summary.decrease', formData.summary.decrease)}
                className="mt-0.5 w-full text-center font-mono text-sm font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 5. 3-COLUMN SALES ROW (المبيعات | مرتجع | صافي البيع)                       */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-3 border-t-2 border-black text-xs">
            {/* Box 1 (Right): المبيعات */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">المبيعات:</div>
              <input
                type="text"
                value={getCellVal('sales.sales', formData.sales.sales)}
                onFocus={() => {
                  setEditingPath('sales.sales');
                  setTempValue(String(formData.sales.sales));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.sales', formData.sales.sales)}
                className="mt-0.5 w-full text-center font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 2 (Center): مرتجع */}
            <div className="border-l-2 border-black p-1">
              <div className="text-[10px] font-bold text-black">مرتجع:</div>
              <input
                type="text"
                value={getCellVal('sales.returns', formData.sales.returns)}
                onFocus={() => {
                  setEditingPath('sales.returns');
                  setTempValue(String(formData.sales.returns));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.returns', formData.sales.returns)}
                className="mt-0.5 w-full text-center font-mono text-sm font-semibold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Box 3 (Left): صافي البيع */}
            <div className="p-1">
              <div className="text-[10px] font-bold text-black">صافي البيع:</div>
              <input
                type="text"
                value={getCellVal('sales.net_sale', formData.sales.net_sale)}
                onFocus={() => {
                  setEditingPath('sales.net_sale');
                  setTempValue(String(formData.sales.net_sale));
                }}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => handleCellBlur('sales.net_sale', formData.sales.net_sale)}
                className="mt-0.5 w-full text-center font-mono text-base font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
              />
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 6. BOTTOM SECTION (ملاحظات على اليمين | المجاميع الكلية على اليسار)         */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-2 border-t-2 border-black text-xs">
            {/* Right Box: ملاحظات */}
            <div className="border-l-2 border-black p-2 flex flex-col">
              <div className="text-[10px] font-bold text-black">ملاحظات:</div>
              <textarea
                rows={3}
                value={getCellVal('notes', approvalNotes)}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="أي ملاحظات إضافية على النموذج..."
                className="mt-1 w-full flex-1 resize-none bg-transparent font-sans text-xs text-black focus:bg-amber-50 focus:outline-none"
              />
            </div>

            {/* Left Box: 3 Stacked Rows */}
            <div className="divide-y-2 divide-black">
              {/* Row 1: المجموع الكلي للبيع: - */}
              <div className="flex items-center justify-between p-1.5">
                <span className="text-[10px] font-bold text-black">المجموع الكلي للبيع: -</span>
                <input
                  type="text"
                  value={getCellVal('sales.total_sale', formData.sales.total_sale)}
                  onFocus={() => {
                    setEditingPath('sales.total_sale');
                    setTempValue(String(formData.sales.total_sale));
                  }}
                  onChange={(e) => setTempValue(e.target.value)}
                  onBlur={() => handleCellBlur('sales.total_sale', formData.sales.total_sale)}
                  className="w-28 text-left font-mono text-base font-black text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                />
              </div>

              {/* Row 2: مجموع التطبيقات:- */}
              <div className="flex items-center justify-between p-1.5">
                <span className="text-[10px] font-bold text-black">مجموع التطبيقات:-</span>
                <input
                  type="text"
                  value={getCellVal('sales.total_applications', formData.sales.total_applications)}
                  onFocus={() => {
                    setEditingPath('sales.total_applications');
                    setTempValue(String(formData.sales.total_applications));
                  }}
                  onChange={(e) => setTempValue(e.target.value)}
                  onBlur={() => handleCellBlur('sales.total_applications', formData.sales.total_applications)}
                  className="w-28 text-left font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                />
              </div>

              {/* Row 3: visa الفيزا:- */}
              <div className="flex items-center justify-between p-1.5">
                <span className="text-[10px] font-bold text-black">visa الفيزا:-</span>
                <input
                  type="text"
                  value={getCellVal('sales.visa_bottom', formData.sales.visa)}
                  onFocus={() => {
                    setEditingPath('sales.visa_bottom');
                    setTempValue(String(formData.sales.visa));
                  }}
                  onChange={(e) => setTempValue(e.target.value)}
                  onBlur={() => {
                    updateFieldMutation.mutate({ path: 'sales.visa', value: tempValue });
                    setEditingPath(null);
                  }}
                  className="w-28 text-left font-mono text-sm font-bold text-black hover:bg-slate-50 focus:bg-amber-50 focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Approval Confirmation Modal */}
      {showApprovalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-emerald-800">
              <ShieldCheck className="h-7 w-7 text-emerald-600" />
              <h3 className="text-lg font-bold">تأكيد الاعتماد النهائي للنموذج المالي</h3>
            </div>

            <div className="mt-4 space-y-3 text-xs text-slate-600">
              {approvalError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 font-semibold text-red-800">
                  {approvalError}
                </div>
              )}
              <p>
                سيتم اعتماد وقفل نموذج يوم <strong>{formData.day_of_week} ({formData.form_date})</strong>.
              </p>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900">
                <ul className="list-inside list-disc space-y-1">
                  <li>سيتم إغلاق النموذج بشكل نهائي ولا يمكن تعديل أرقامه بعد الاعتماد.</li>
                  <li>يُسمح بنموذج معتمد واحد فقط لكل تاريخ ميلادي.</li>
                  <li>سيتم حذف الصور المؤقتة فوراً من الخادم للامتثال الأمني.</li>
                  <li>سيتم إلحاق البيانات بمصنف Excel وتوليد تقرير PDF المعتمد المطابق للورقة.</li>
                </ul>
              </div>

              {formData.calculation_mismatches.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <label className="flex items-start gap-2 font-semibold text-red-900">
                    <input
                      type="checkbox"
                      checked={forceOverride}
                      onChange={(e) => setForceOverride(e.target.checked)}
                      className="mt-0.5 rounded text-red-600 focus:ring-red-500"
                    />
                    <span>أؤكد وجود فروقات حسابية وأرغب في اعتماد النموذج مع تجاوز التحقق الحسابي بشكل صريح.</span>
                  </label>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowApprovalModal(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                تراجع
              </button>
              <button
                type="button"
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending || (formData.calculation_mismatches.length > 0 && !forceOverride)}
                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {approveMutation.isPending ? 'جاري الاعتماد...' : 'تأكيد الاعتماد والقفل'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
