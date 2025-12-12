import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2, Phone, KeyRound, Lock, Clock, AlertTriangle } from 'lucide-react';
import { PasswordInput } from '../ui/PasswordInput';
import { client } from '../../api/client';

// Define schemas
const phoneSchema = z.object({
  phone: z.string().min(5, "Phone number is too short"),
});

const codeSchema = z.object({
  code: z.string().length(5, "Code must be 5 digits"),
});

const passwordSchema = z.object({
  password: z.string().min(1, "Password is required"),
});

type PhoneForm = z.infer<typeof phoneSchema>;
type CodeForm = z.infer<typeof codeSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

interface RateLimitInfo {
  type: string;
  message: string;
  wait_seconds: number;
  remaining_seconds: number;
  retry_after?: string;
}

interface TelegramLoginProps {
  onSuccess: (token?: string) => void;
  apiPrefix?: string; // Default: '/api/auth/telegram', для страницы входа: '/api/auth/telegram-login'
}

// Компонент таймера обратного отсчёта
const CountdownTimer: React.FC<{ 
  seconds: number; 
  onComplete: () => void;
  message: string;
}> = ({ seconds, onComplete, message }) => {
  const [remaining, setRemaining] = useState(seconds);
  
  useEffect(() => {
    if (remaining <= 0) {
      onComplete();
      return;
    }
    const timer = setInterval(() => {
      setRemaining(prev => {
        if (prev <= 1) {
          onComplete();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [remaining, onComplete]);
  
  const formatTime = (secs: number) => {
    if (secs < 60) return `${secs} сек.`;
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    if (mins < 60) return `${mins}:${s.toString().padStart(2, '0')}`;
    const hours = Math.floor(mins / 60);
    const m = mins % 60;
    return `${hours}ч ${m}м`;
  };
  
  return (
    <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
      <Clock className="h-5 w-5 text-amber-600 dark:text-amber-400" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">{message}</p>
        <p className="text-lg font-bold text-amber-900 dark:text-amber-100">{formatTime(remaining)}</p>
      </div>
    </div>
  );
};

export const TelegramLogin: React.FC<TelegramLoginProps> = ({ onSuccess, apiPrefix = '/api/auth/telegram' }) => {
  const [step, setStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);

  const phoneForm = useForm<PhoneForm>({ resolver: zodResolver(phoneSchema) });
  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
  const passwordForm = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  // Парсинг ошибки rate limit из ответа API
  const parseRateLimitError = (err: any): RateLimitInfo | null => {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'object' && detail?.error === 'rate_limit') {
      return detail as RateLimitInfo;
    }
    // Проверяем строковые сообщения об ошибках лимитов
    const errorStr = typeof detail === 'string' ? detail : String(detail);
    if (errorStr.includes('FLOOD') || errorStr.includes('UNAVAILABLE') || errorStr.includes('wait')) {
      return {
        type: 'unknown',
        message: errorStr,
        wait_seconds: 60, // Дефолтное время ожидания
        remaining_seconds: 60,
      };
    }
    return null;
  };

  const handleError = (err: any) => {
    const limitInfo = parseRateLimitError(err);
    if (limitInfo) {
      setRateLimit(limitInfo);
      setError('');
    } else {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Произошла ошибка');
      setRateLimit(null);
    }
  };

  const onPhoneSubmit = async (data: PhoneForm) => {
    setLoading(true);
    setError('');
    setRateLimit(null);
    try {
      await client.post(`${apiPrefix}/send-code`, { phone: data.phone });
      setPhone(data.phone);
      setStep('code');
    } catch (err: any) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const onCodeSubmit = async (data: CodeForm) => {
    setLoading(true);
    setError('');
    setRateLimit(null);
    try {
      const res = await client.post(`${apiPrefix}/login`, {
        phone,
        code: data.code,
      });
      
      if (res.data.status === '2fa_required') {
        setCode(data.code);
        setStep('password');
      } else {
        // Если есть токен - передаём его
        onSuccess(res.data.access_token);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail;
      // Специальная обработка истёкшего кода с подсказкой
      if (typeof errorMsg === 'string' && errorMsg.includes('Code expired')) {
        setError('⏱️ Код истёк. Нажмите кнопку "🔄 Запросить новый код" ниже.');
      } else {
        handleError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordForm) => {
    setLoading(true);
    setError('');
    setRateLimit(null);
    try {
      const res = await client.post(`${apiPrefix}/login`, {
        phone,
        code,
        password: data.password,
      });
      onSuccess(res.data.access_token);
    } catch (err: any) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-4">
      <h2 className="text-xl font-bold mb-4 text-center text-white">
        <span className="flex items-center justify-center gap-2">
          <Phone className="h-5 w-5" />
          Telegram Login
        </span>
      </h2>
      
      {/* Rate Limit Warning */}
      {rateLimit && (
        <div className="mb-4">
          <CountdownTimer
            seconds={rateLimit.remaining_seconds}
            message={rateLimit.message}
            onComplete={() => setRateLimit(null)}
          />
        </div>
      )}
      
      {/* Regular Error */}
      {error && !rateLimit && (
        <div className="mb-4 p-3 bg-red-900/30 text-red-300 rounded-md text-sm flex items-start gap-2 border border-red-700">
          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {step === 'phone' && (
        <form onSubmit={phoneForm.handleSubmit(onPhoneSubmit)} action="" autoComplete="on" className="space-y-4">
          <div>
            <label htmlFor="phone" className="block text-sm font-medium mb-1 text-gray-300">Номер телефона</label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                {...phoneForm.register('phone')}
                id="phone"
                type="tel"
                name="phone"
                autoComplete="tel"
                placeholder="+380XXXXXXXXX"
                className="w-full pl-10 pr-3 py-2 border rounded-md bg-gray-800 border-gray-600 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            {phoneForm.formState.errors.phone && (
              <p className="text-red-400 text-xs mt-1">{phoneForm.formState.errors.phone.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Отправить код'}
          </button>
        </form>
      )}

      {step === 'code' && (
        <form onSubmit={codeForm.handleSubmit(onCodeSubmit)} action="" autoComplete="off" className="space-y-4">
          <div>
            <label htmlFor="code" className="block text-sm font-medium mb-1 text-gray-300">Код подтверждения</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                {...codeForm.register('code')}
                id="code"
                type="text"
                name="code"
                autoComplete="one-time-code"
                placeholder="12345"
                maxLength={5}
                inputMode="numeric"
                className="w-full pl-10 pr-3 py-2 border rounded-md bg-gray-800 border-gray-600 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-lg tracking-widest"
              />
            </div>
            {codeForm.formState.errors.code && (
              <p className="text-red-400 text-xs mt-1">{codeForm.formState.errors.code.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Проверить код'}
          </button>
          <div className="p-3 bg-blue-900/30 rounded-md text-sm text-blue-200 border border-blue-700">
            <p className="font-medium mb-1">📱 Проверьте приложение Telegram!</p>
            <p className="text-xs text-blue-300">
              Код отправлен в ваш Telegram от пользователя <strong>&quot;Telegram&quot;</strong> (ID: 777000).
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={async () => {
                setLoading(true);
                setError('');
                setRateLimit(null);
                try {
                  await client.post(`${apiPrefix}/resend-code`, { phone });
                  setError('');
                  // Можно показать success toast
                } catch (err: any) {
                  handleError(err);
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading || !!rateLimit}
              className="flex-1 py-2 px-3 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md disabled:opacity-50 transition-colors"
            >
              {loading ? <Loader2 className="animate-spin h-4 w-4 mx-auto" /> : '🔄 Запросить новый код'}
            </button>
            <button
              type="button"
              onClick={() => setStep('phone')}
              className="py-2 px-3 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              ← Назад
            </button>
          </div>
        </form>
      )}

      {step === 'password' && (
        <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} action="" autoComplete="on" className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1 text-gray-300 flex items-center gap-2">
              <Lock className="h-4 w-4 text-gray-400" />
              Пароль 2FA
            </label>
            <PasswordInput
              {...passwordForm.register('password')}
              id="password"
              name="password"
              autoComplete="current-password"
              placeholder="Введите пароль 2FA"
              className="w-full px-4 py-2 border rounded-md bg-gray-800 border-gray-600 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              buttonClassName="text-gray-400 hover:text-gray-200"
              iconSize={20}
            />
            {passwordForm.formState.errors.password && (
              <p className="text-red-400 text-xs mt-1">{passwordForm.formState.errors.password.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Войти'}
          </button>
          <button
            type="button"
            onClick={() => setStep('code')}
            className="w-full text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            ← Назад к коду
          </button>
        </form>
      )}
    </div>
  );
};
