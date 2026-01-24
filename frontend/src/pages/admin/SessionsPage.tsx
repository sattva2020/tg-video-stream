import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '@/components/layout';
import { SessionHealthList } from '@/components/admin/telegram-sessions/SessionHealthList';

export const SessionsPage: React.FC = () => {
  const { t } = useTranslation();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleConfigureClick = (sessionId: string) => {
    // TODO: Open configuration modal
    console.log('Configure session:', sessionId);
  };

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Telegram Sessions</h1>
          <p className="text-muted-foreground">
            Monitor and manage Telegram session health, refresh settings, and 2FA configuration
          </p>
        </div>

        <SessionHealthList
          refreshTrigger={refreshTrigger}
          onConfigureClick={handleConfigureClick}
        />
      </div>
    </AppLayout>
  );
};

export default SessionsPage;
