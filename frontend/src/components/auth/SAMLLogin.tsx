import React from 'react';
import { Shield } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';

interface SAMLLoginProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export const SAMLLogin: React.FC<SAMLLoginProps> = ({
  onClick,
  disabled = false,
  className = '',
}) => {
  const { t } = useTranslation();

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-full',
        'bg-[#F5E6D3]/10 text-[#F5E6D3] border border-[#F5E6D3]/30',
        'hover:shadow-[0_0_20px_rgba(245,230,211,0.2)] hover:bg-[#F5E6D3]/20 hover:border-[#F5E6D3]/50',
        'transition-all duration-300 disabled:opacity-50',
        className
      )}
    >
      <Shield className="w-5 h-5" />
      <span>{t('login_saml', 'Войти через SSO')}</span>
    </button>
  );
};

export default SAMLLogin;
