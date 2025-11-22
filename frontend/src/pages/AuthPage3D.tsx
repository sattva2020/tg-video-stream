import React, { useState, useEffect, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import ZenScene from '../components/ZenScene';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { LoginSchema, RegisterSchema, type LoginRequest, authApi } from '../api/auth';
import { useNavigate } from 'react-router-dom';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff, Globe } from 'lucide-react';
import { z } from 'zod';
import { useAuth } from '../context/AuthContext';

type AuthMode = 'login' | 'register';

const AuthPage3D: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [mode, setMode] = useState<AuthMode>('login');
  const [scrollY, setScrollY] = useState(0);
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (window.location.pathname.includes('/register')) setMode('register');
    if (window.location.pathname.includes('/login')) setMode('login');
  }, []);

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setErrorMessage(null);
  };

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    setShowLanguageMenu(false);
  };

  return (
    <div className="relative w-full min-h-screen overflow-hidden bg-parchment text-ink font-lato">
      {/* 3D Background */}
      <div className="fixed inset-0 z-0 opacity-100 pointer-events-none">
        <Canvas camera={{ position: [0, 0, 8], fov: 45 }} gl={{ alpha: true }}>
          <Suspense fallback={null}>
            <ZenScene scrollY={scrollY} />
          </Suspense>
        </Canvas>
      </div>

      {/* Language Switcher */}
      <div className="absolute top-4 right-4 z-50">
        <div className="relative">
          <button
            onClick={() => setShowLanguageMenu(!showLanguageMenu)}
            className="flex items-center space-x-2 px-3 py-2 bg-white/10 backdrop-blur-md rounded-lg text-white hover:bg-white/20 transition-colors"
          >
            <Globe size={20} />
            <span className="uppercase">{i18n.language}</span>
          </button>

          {showLanguageMenu && (
            <div className="absolute right-0 mt-2 w-32 bg-white rounded-lg shadow-xl overflow-hidden py-1">
              {['en', 'ru', 'uk', 'de'].map((lng) => (
                <button
                  key={lng}
                  onClick={() => changeLanguage(lng)}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 uppercase"
                >
                  {lng}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Content Overlay */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-12 pointer-events-none">
        <div className="pointer-events-auto w-full max-w-md animate-float">
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="glass-morphism border border-ink/10 rounded-3xl shadow-2xl overflow-hidden bg-white/10 backdrop-blur-lg"
          >
            <div className="p-10">
              <div className="text-center mb-10">
                <motion.h1
                  className="text-5xl font-cinzel font-bold tracking-widest text-white mb-3"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  {mode === 'login' ? t('sattva') : t('join_us')}
                </motion.h1>
                <motion.p
                  className="text-sm text-white/70 font-lato tracking-wide uppercase"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                >
                  {mode === 'login' ? t('enter_stream') : t('begin_journey')}
                </motion.p>
              </div>

              <AnimatePresence mode="wait">
                {mode === 'login' ? (
                  <LoginForm
                    key="login"
                    onSuccess={() => navigate('/dashboard')}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                    setErrorMessage={setErrorMessage}
                    t={t}
                  />
                ) : (
                  <RegisterForm
                    key="register"
                    onSuccess={() => navigate('/dashboard')}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                    setErrorMessage={setErrorMessage}
                    t={t}
                  />
                )}
              </AnimatePresence>

              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-4 p-3 text-sm text-center text-red-200 bg-red-900/50 border border-red-500/30 rounded-lg font-lato"
                >
                  {errorMessage}
                </motion.div>
              )}

              <div className="mt-8">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/10" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase font-lato">
                    <span className="px-3 bg-transparent text-white/50">{t('or_continue')}</span>
                  </div>
                </div>

                <div className="mt-6">
                  <GoogleLoginButton onClick={() => window.location.href = '/api/auth/google'} disabled={isLoading} />
                </div>
              </div>

              <div className="mt-8 text-center">
                <button
                  onClick={toggleMode}
                  className="text-sm text-white/80 hover:text-white transition-colors duration-200 font-medium font-lato underline decoration-white/30 hover:decoration-white/80"
                >
                  {mode === 'login'
                    ? t('dont_have_account')
                    : t('already_have_account')}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

const LoginForm = ({ onSuccess, isLoading, setIsLoading, setErrorMessage, t }: any) => {
  const { register, handleSubmit, formState: { errors } } = useForm<LoginRequest>({
    resolver: zodResolver(LoginSchema),
  });
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();

  const onSubmit = async (data: LoginRequest) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await authApi.login(data);
      await login(response.access_token);
      onSuccess();
    } catch (error: any) {
      if (error.response?.status === 401) {
        setErrorMessage(t('invalid_credentials'));
      } else {
        setErrorMessage(t('login_failed'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.form
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5 font-lato"
    >
      <div>
        <input
          {...register('username')}
          type="email"
          placeholder={t('email')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all"
        />
        {errors.username && <p className="mt-2 text-xs text-red-400">{errors.username.message}</p>}
      </div>
      <div className="relative">
        <input
          {...register('password')}
          type={showPassword ? "text" : "password"}
          placeholder={t('password')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all pr-12"
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white"
        >
          {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
        </button>
        {errors.password && <p className="mt-2 text-xs text-red-400">{errors.password.message}</p>}
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-4 px-6 bg-white text-black font-semibold rounded-xl shadow-lg transform transition-all hover:scale-[1.02] active:scale-[0.98] ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isLoading ? t('entering') : t('enter')}
      </button>
    </motion.form>
  );
};

// Extended Schema for Registration with Confirm Password
const RegisterFormSchema = RegisterSchema.extend({
  confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
  message: "passwords_mismatch", // Key for translation
  path: ["confirmPassword"],
});

type RegisterFormRequest = z.infer<typeof RegisterFormSchema>;

const RegisterForm = ({ onSuccess, isLoading, setIsLoading, setErrorMessage, t }: any) => {
  const { register, handleSubmit, formState: { errors } } = useForm<RegisterFormRequest>({
    resolver: zodResolver(RegisterFormSchema),
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const { login } = useAuth();

  const onSubmit = async (data: RegisterFormRequest) => {
    setIsLoading(true);
    setErrorMessage(null);
      try {
        // Remove confirmPassword before sending to API
        const { confirmPassword, ...apiData } = data;
        const response = await authApi.register(apiData);
        // If backend returns an access_token (dev-mode or special cases) we log in
        if ((response as any).access_token) {
          await login((response as any).access_token);
          onSuccess();
        } else if ((response as any).status === 'pending') {
          // User is created but awaiting admin approval — inform user and stop
          setErrorMessage((response as any).message || t('account_pending'));
        } else {
          // Fallback behaviour
          setErrorMessage(t('registration_failed'));
        }
    } catch (error: any) {
      if (error.response?.status === 400) {
        setErrorMessage(error.response?.data?.detail || t('email_exists'));
      } else {
        setErrorMessage(t('registration_failed'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.form
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5 font-lato"
    >
      <div>
        <input
          {...register('email')}
          type="email"
          placeholder={t('email')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all"
        />
        {errors.email && <p className="mt-2 text-xs text-red-400">{errors.email.message}</p>}
      </div>
      <div>
        <input
          {...register('full_name')}
          type="text"
          placeholder={t('full_name')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all"
        />
      </div>
      <div className="relative">
        <input
          {...register('password')}
          type={showPassword ? "text" : "password"}
          placeholder={t('password')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all pr-12"
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white"
        >
          {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
        </button>
        {errors.password && <p className="mt-2 text-xs text-red-400">{errors.password.message}</p>}
        <p className="mt-2 text-[10px] text-white/50">
          {t('password_requirements')}
        </p>
      </div>
      <div className="relative">
        <input
          {...register('confirmPassword')}
          type={showConfirmPassword ? "text" : "password"}
          placeholder={t('confirm_password')}
          className="w-full px-5 py-4 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/30 focus:border-transparent outline-none text-white placeholder-white/40 transition-all pr-12"
        />
        <button
          type="button"
          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white"
        >
          {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
        </button>
        {errors.confirmPassword && <p className="mt-2 text-xs text-red-400">{t(errors.confirmPassword.message as string)}</p>}
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className={`w-full py-4 px-6 bg-white text-black font-semibold rounded-xl shadow-lg transform transition-all hover:scale-[1.02] active:scale-[0.98] ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isLoading ? t('joining') : t('begin')}
      </button>
    </motion.form>
  );
};

export default AuthPage3D;
