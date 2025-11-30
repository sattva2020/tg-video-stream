import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import axios from 'axios';
import { Loader2, Phone, KeyRound, Lock } from 'lucide-react';
import { PasswordInput } from '../ui/PasswordInput';

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

interface TelegramLoginProps {
  onSuccess: () => void;
}

export const TelegramLogin: React.FC<TelegramLoginProps> = ({ onSuccess }) => {
  const [step, setStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const phoneForm = useForm<PhoneForm>({ resolver: zodResolver(phoneSchema) });
  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
  const passwordForm = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const client = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    withCredentials: true,
  });

  const onPhoneSubmit = async (data: PhoneForm) => {
    setLoading(true);
    setError('');
    try {
      await client.post('/api/auth/telegram/send-code', { phone: data.phone });
      setPhone(data.phone);
      setStep('code');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const onCodeSubmit = async (data: CodeForm) => {
    setLoading(true);
    setError('');
    try {
      const res = await client.post('/api/auth/telegram/login', {
        phone,
        code: data.code,
      });
      
      if (res.data.status === '2fa_required') {
        setCode(data.code);
        setStep('password');
      } else {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordForm) => {
    setLoading(true);
    setError('');
    try {
      await client.post('/api/auth/telegram/login', {
        phone,
        code,
        password: data.password,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center dark:text-white">Telegram Login</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      {step === 'phone' && (
        <form onSubmit={phoneForm.handleSubmit(onPhoneSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-300">Phone Number</label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                {...phoneForm.register('phone')}
                placeholder="+1234567890"
                className="w-full pl-10 pr-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {phoneForm.formState.errors.phone && (
              <p className="text-red-500 text-xs mt-1">{phoneForm.formState.errors.phone.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Send Code'}
          </button>
        </form>
      )}

      {step === 'code' && (
        <form onSubmit={codeForm.handleSubmit(onCodeSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-300">Verification Code</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                {...codeForm.register('code')}
                placeholder="12345"
                className="w-full pl-10 pr-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {codeForm.formState.errors.code && (
              <p className="text-red-500 text-xs mt-1">{codeForm.formState.errors.code.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Verify Code'}
          </button>
          <button
            type="button"
            onClick={() => setStep('phone')}
            className="w-full text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
          >
            Back to Phone
          </button>
        </form>
      )}

      {step === 'password' && (
        <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-300">2FA Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4 z-10" />
              <PasswordInput
                {...passwordForm.register('password')}
                placeholder="******"
                className="w-full pl-10 pr-12 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500"
                iconSize={16}
              />
            </div>
            {passwordForm.formState.errors.password && (
              <p className="text-red-500 text-xs mt-1">{passwordForm.formState.errors.password.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md flex items-center justify-center disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin h-4 w-4" /> : 'Sign In'}
          </button>
          <button
            type="button"
            onClick={() => setStep('code')}
            className="w-full text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
          >
            Back to Code
          </button>
        </form>
      )}
    </div>
  );
};
