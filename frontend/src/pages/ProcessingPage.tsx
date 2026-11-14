import React, { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useI18n } from '../i18n/context';
import { api } from '../services/api';
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  ArrowRight,
  Eye,
} from 'lucide-react';

export const ProcessingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { language, t, dir } = useI18n();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const Arrow = dir === 'rtl' ? ArrowLeft : ArrowRight;

  const { data: statusData, isLoading } = useQuery({
    queryKey: ['docStatus', id],
    queryFn: () => api.processing.getStatus(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (s === 'ready_for_review' || s === 'approved' || s === 'failed') {
        return false;
      }
      return 2500;
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => api.processing.retry(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docStatus', id] });
    },
  });

  const progress = statusData?.progress_percentage ?? 10;
  const status = statusData?.status;
  const isComplete = status === 'ready_for_review' || status === 'approved';
  const isFailed = status === 'failed';

  useEffect(() => {
    if (isComplete) {
      const timer = setTimeout(() => {
        navigate(`/review/${id}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isComplete, id, navigate]);

  const stages = [
    { label: 'تحسين ومعالجة ميل الصورة', target: 30 },
    { label: 'استخراج نصوص OCR وإحداثيات الكلمات', target: 60 },
    { label: 'فهم الجداول واستخراج البيانات المنظمة بالذكاء الاصطناعي', target: 90 },
    { label: 'التحقق الصارم والمطابقة الهيكلية', target: 100 },
  ];

  return (
    <div className="max-w-2xl mx-auto py-12 space-y-8 text-center">
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 mx-auto flex items-center justify-center animate-pulse">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">
          {isComplete
            ? 'اكتملت المعالجة بنجاح!'
            : isFailed
            ? 'تعثرت معالجة المستند'
            : 'جاري استخراج وتحليل بيانات المستند...'}
        </h2>
        <p className="text-sm text-slate-500">
          {statusData?.stage || 'يتم تشغيل خط أنابيب المعالجة الذكي'}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
          <span>{isComplete ? '100%' : `${progress}%`}</span>
          <span>{isComplete ? 'جاهز للمراجعة' : 'قيد التقدم'}</span>
        </div>

        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              isFailed ? 'bg-rose-500' : 'bg-emerald-600'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Pipeline Stage Indicators */}
        <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-right">
          {stages.map((stage, i) => {
            const stageDone = progress >= stage.target;
            return (
              <div
                key={i}
                className={`p-3 rounded-lg border text-xs flex items-center gap-2.5 ${
                  stageDone
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <CheckCircle2
                  className={`w-4 h-4 ${stageDone ? 'text-emerald-600' : 'text-slate-300'}`}
                />
                <span className="font-medium">{stage.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      {isComplete && (
        <div className="pt-2">
          <Link
            to={`/review/${id}`}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 text-white font-semibold hover:bg-emerald-700 shadow-md transition"
          >
            <Eye className="w-5 h-5" />
            <span>الانتقال فوراً إلى شاشة المراجعة والاعتماد</span>
            <Arrow className="w-4 h-4" />
          </Link>
        </div>
      )}

      {isFailed && (
        <div className="bg-rose-50 border border-rose-200 p-6 rounded-xl text-right space-y-4">
          <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
            <AlertCircle className="w-5 h-5 text-rose-600" />
            <span>تفاصيل الخطأ:</span>
          </div>
          <p className="text-xs text-rose-700 bg-white p-3 rounded border border-rose-100 font-mono">
            {statusData?.error_message || 'حدث خطأ غير متوقع أثناء معالجة المستند.'}
          </p>
          <div className="flex justify-end gap-3">
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
            >
              العودة للوحة التحكم
            </Link>
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold"
            >
              <RefreshCw className="w-4 h-4" />
              <span>إعادة المحاولة</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
