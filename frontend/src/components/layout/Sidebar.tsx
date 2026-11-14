import React from 'react';
import { NavLink } from 'react-router-dom';
import { useI18n } from '../../i18n/context';
import {
  LayoutDashboard,
  UploadCloud,
  Settings as SettingsIcon,
  Globe,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { language, setLanguage, t } = useI18n();

  const navItems = [
    { to: '/dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { to: '/upload', label: t('upload'), icon: UploadCloud },
    { to: '/settings', label: t('settings'), icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-white border-l border-r border-slate-200 min-h-screen sticky top-0 h-screen p-4 flex flex-col justify-between flex-shrink-0 z-20">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2 py-2 border-b border-slate-100 pb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-emerald-600/20">
            أ
          </div>
          <div>
            <h1 className="font-extrabold text-slate-900 text-base leading-tight tracking-tight">
              # hasep
            </h1>
            <p className="text-[11px] text-slate-500 font-medium">
              {language === 'ar' ? 'رقمنة النماذج المالية اليومية' : 'Daily Financial Digitization'}
            </p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-800 font-semibold shadow-xs border border-emerald-100'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                <Icon className="w-5 h-5 text-slate-500" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Language Switcher */}
      <div className="space-y-3">
        {/* Language Switch */}
        <button
          onClick={() => setLanguage(language === 'ar' ? 'en' : 'ar')}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-slate-200 text-xs text-slate-600 hover:bg-slate-50 transition"
        >
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-slate-400" />
            <span>{language === 'ar' ? 'اللغة / Language' : 'Language / اللغة'}</span>
          </div>
          <span className="font-bold text-emerald-700">{language === 'ar' ? 'العربية' : 'English'}</span>
        </button>
      </div>
    </aside>
  );
};
