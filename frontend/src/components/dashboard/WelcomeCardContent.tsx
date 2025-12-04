import React from 'react';
import { Card, CardBody, Chip } from '@heroui/react';
import { CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { User } from '../../types/user';

interface WelcomeCardContentProps {
  user: User | null;
}

interface StatusItem {
  id: string;
  label: string;
  value: string;
  positive: boolean;
}

export const WelcomeCardContent: React.FC<WelcomeCardContentProps> = ({ user }) => {
  const { t } = useTranslation();

  const statusItems: StatusItem[] = [
    {
      id: 'account',
      label: t('user.status.account', 'Статус аккаунта'),
      value: user?.status === 'active'
        ? t('user.status.active', 'Активен')
        : t('user.status.pending', 'Ожидает одобрения'),
      positive: user?.status === 'active',
    },
    {
      id: 'email',
      label: t('user.status.email', 'Email подтверждён'),
      value: user?.email ?? t('user.status.emailMissing', 'Не указан'),
      positive: Boolean(user?.email),
    },
    {
      id: 'telegram',
      label: t('user.status.telegram', 'Telegram подключён'),
      value: user?.telegram_username
        ? `@${user.telegram_username}`
        : t('user.status.telegramMissing', 'Не подключён'),
      positive: Boolean(user?.telegram_username),
    },
    {
      id: 'role',
      label: t('user.status.role', 'Ваша роль'),
      value: t(`roles.${user?.role ?? 'user'}`, (user?.role ?? 'user').toString().toUpperCase()),
      positive: true,
    },
    {
      id: 'lastLogin',
      label: t('user.status.lastLogin', 'Последний вход'),
      value: t('user.status.lastLoginUnknown', 'Нет данных'),
      positive: false,
    },
  ];

  const tips: string[] = [
    t('user.tips.connectTelegram', 'Подключите Telegram, чтобы получать уведомления о трансляциях'),
    t('user.tips.checkSchedule', 'Проверяйте расписание эфиров перед выходом в эфир'),
    t('user.tips.manageChannels', 'Управляйте каналами в разделе «Менеджер каналов»'),
  ];

  return (
    <div className="space-y-6 w-full">
      <div className="grid gap-4 md:grid-cols-2">
        {statusItems.map((item) => (
          <Card key={item.id} className="border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)]">
            <CardBody className="flex items-start gap-3 p-4">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  item.positive ? 'bg-emerald-500/15 text-emerald-500' : 'bg-amber-500/15 text-amber-500'
                }`}
              >
                {item.positive ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-[color:var(--color-text-muted)]">{item.label}</p>
                {item.id === 'role' ? (
                  <Chip
                    size="sm"
                    variant="flat"
                    color="secondary"
                    className="mt-2 text-[color:var(--color-text)]"
                  >
                    {item.value}
                  </Chip>
                ) : (
                  <p className="text-sm font-semibold text-[color:var(--color-text)] mt-1">{item.value}</p>
                )}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-500/10 via-violet-500/10 to-fuchsia-500/10 border border-[color:var(--color-border)]">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-5 h-5 text-violet-500" />
          <h3 className="text-base font-semibold text-[color:var(--color-text)]">
            {t('user.tips.title', 'Советы по использованию')}
          </h3>
        </div>
        <ul className="space-y-2 text-sm">
          {tips.map((tip, index) => (
            <li key={index} className="flex items-start gap-2 text-[color:var(--color-text)]">
              <span className="mt-1 block w-1.5 h-1.5 rounded-full bg-violet-500" />
              <span className="text-[color:var(--color-text-muted)]">{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
