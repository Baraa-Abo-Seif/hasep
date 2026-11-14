import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useI18n } from '../i18n/context';
import { api } from '../services/api';
import {
  UploadCloud,
  FileText,
  Image as ImageIcon,
  X,
  CheckCircle2,
  AlertCircle,
  Play,
} from 'lucide-react';

export const UploadPage: React.FC = () => {
  const { language, t } = useI18n();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [autoProcess, setAutoProcess] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => api.documents.upload(selectedFiles, autoProcess),
    onSuccess: (response: any) => {
      const docs = Array.isArray(response) ? response : response?.data || [];
      if (docs && docs.length > 0) {
        const firstDoc = docs[0];
        if (autoProcess) {
          navigate(`/processing/${firstDoc.id}`);
        } else {
          navigate('/dashboard');
        }
      } else {
        navigate('/dashboard');
      }
    },
    onError: (err: any) => {
      setErrorMessage(err.response?.data?.detail || err.message || 'حدث خطأ أثناء رفع الملفات.');
    },
  });

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    setErrorMessage(null);

    const validFiles: File[] = [];
    const validPreviews: string[] = [];

    Array.from(files).forEach((file) => {
      // Validate size (< 25MB)
      if (file.size > 25 * 1024 * 1024) {
        setErrorMessage(`الملف ${file.name} يتجاوز الحجم المسموح به (25 ميجابايت).`);
        return;
      }
      validFiles.push(file);
      if (file.type.startsWith('image/')) {
        validPreviews.push(URL.createObjectURL(file));
      } else {
        validPreviews.push('');
      }
    });

    setSelectedFiles((prev) => [...prev, ...validFiles]);
    setPreviews((prev) => [...prev, ...validPreviews]);
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">رفع نموذج الإغلاق المالي اليومي</h2>
        <p className="text-sm text-slate-500">
          ارفع صورة أو ملف PDF لنموذج الإغلاق المالي وسجل الدوام اليومي المكتوب بخط اليد للمعالجة عبر الذكاء الاصطناعي (Gemini Vision)
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-2xl p-10 text-center cursor-pointer bg-white hover:bg-emerald-50/20 transition group"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 mx-auto flex items-center justify-center group-hover:scale-105 transition">
          <UploadCloud className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 mt-4">{t('dragDropTitle')}</h3>
        <p className="text-sm text-slate-500 mt-1">{t('supportedFormats')}</p>
      </div>

      {/* Selected Files List & Preview */}
      {selectedFiles.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm">
              الملفات المحددة ({selectedFiles.length})
            </h4>
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={autoProcess}
                onChange={(e) => setAutoProcess(e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
              />
              <span>البدء التلقائي في التحليل والاستخراج بعد الرفع</span>
            </label>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="relative rounded-lg border border-slate-200 p-3 flex items-center gap-3 bg-slate-50"
              >
                <div className="w-12 h-12 rounded bg-white border border-slate-200 overflow-hidden flex-shrink-0 flex items-center justify-center">
                  {previews[idx] ? (
                    <img src={previews[idx]} alt={file.name} className="w-full h-full object-cover" />
                  ) : (
                    <FileText className="w-6 h-6 text-slate-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-slate-900 truncate">{file.name}</p>
                  <p className="text-[11px] text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="p-1 rounded-full text-slate-400 hover:text-rose-600 hover:bg-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <div className="pt-4 flex justify-end">
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md transition disabled:opacity-50"
            >
              {uploadMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>جاري رفع ومعالجة المستندات...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>{t('startProcessing')}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
