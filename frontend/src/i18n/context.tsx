import React, { createContext, useContext, useState, useEffect } from 'react';

type Language = 'ar' | 'en';

interface Translations {
  [key: string]: {
    ar: string;
    en: string;
  };
}

const translations: Translations = {
  appName: {
    ar: '# hasep',
    en: '# hasep',
  },
  dashboard: { ar: 'لوحة التحكم', en: 'Dashboard' },
  upload: { ar: 'رفع مستند جديد', en: 'Upload Document' },
  review: { ar: 'المراجعة والاعتماد', en: 'Review & Approval' },
  export: { ar: 'المزامنة السحابية', en: 'Cloud Sync' },
  settings: { ar: 'الإعدادات', en: 'Settings' },
  googleConnected: { ar: 'متصل بحساب Google', en: 'Connected to Google' },
  googleDisconnected: { ar: 'غير متصل بـ Google', en: 'Google Disconnected' },
  connectGoogle: { ar: 'ربط حساب Google', en: 'Connect Google' },
  disconnectGoogle: { ar: 'فصل الحساب', en: 'Disconnect' },
  totalDocuments: { ar: 'إجمالي المستندات', en: 'Total Documents' },
  pendingReviews: { ar: 'بانتظار المراجعة', en: 'Pending Reviews' },
  successfulExports: { ar: 'مزامنة ناجحة', en: 'Successful Syncs' },
  failedOperations: { ar: 'عمليات غير مكتملة', en: 'Failed Operations' },
  dragDropTitle: { ar: 'اسحب وأفلت الصور هنا، أو انقر للاختيار', en: 'Drag and drop images here, or click to browse' },
  supportedFormats: { ar: 'ندعم ملفات JPG و PNG و WebP و PDF (حتى 25 ميجابايت)', en: 'Supports JPG, PNG, WebP, PDF (up to 25MB)' },
  startProcessing: { ar: 'بدء الاستخراج والتحليل الذكي', en: 'Start AI Extraction' },
  processingStatus: { ar: 'حالة المعالجة', en: 'Processing Status' },
  approveData: { ar: 'اعتماد البيانات', en: 'Approve Data' },
  rejectData: { ar: 'رفض النتيجة', en: 'Reject Extraction' },
  exportToExcel: { ar: 'مزامنة Google Sheets', en: 'Google Sheets Sync' },
  selectWorkbook: { ar: 'ملف Google Sheets', en: 'Google Spreadsheet' },
  selectWorksheet: { ar: 'الورقة الشهرية', en: 'Monthly Sheet' },
  selectTable: { ar: 'اختر الجدول الهدف', en: 'Select Target Table' },
  confirmExport: { ar: 'تأكيد التصدير النهائي', en: 'Confirm Final Export' },
  viewOriginalImage: { ar: 'معاينة الصورة الأصلية', en: 'Original Image Preview' },
  extractedTableTitle: { ar: 'الجدول المستخرج والقابل للتعديل', en: 'Extracted Editable Table' },
  needsReviewNotice: { ar: 'تنبيه: توجد خانات غير مؤكدة أو تحتاج إلى مراجعة', en: 'Notice: Some cells are uncertain and require review' },
  originalValue: { ar: 'النص الأصلي (OCR):', en: 'Original Text (OCR):' },
  aiNormalizedValue: { ar: 'القيمة المستخرجة (AI):', en: 'Extracted Value (AI):' },
};

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
  dir: 'rtl' | 'ltr';
}

const I18nContext = createContext<I18nContextType>({
  language: 'ar',
  setLanguage: () => {},
  t: (k) => k,
  dir: 'rtl',
});

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    return (localStorage.getItem('lang') as Language) || 'ar';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('lang', lang);
  };

  const dir = language === 'ar' ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [language, dir]);

  const t = (key: string): string => {
    if (translations[key]) {
      return translations[key][language];
    }
    return key;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t, dir }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = () => useContext(I18nContext);
