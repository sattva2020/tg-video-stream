import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '@/components/layout';
import { SessionHealthList } from '@/components/admin/telegram-sessions/SessionHealthList';
import { SessionConfigModal } from '@/components/admin/telegram-sessions/SessionConfigModal';

export const SessionsPage: React.FC = () => {
  const { t } = useTranslation();
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [configModalSession, setConfigModalSession] = useState<{
    id: string;
    phone?: string;
  } | null>(null);

  const handleConfigureClick = (sessionId: string, sessionPhone?: string) => {
    setConfigModalSession({ id: sessionId, phone: sessionPhone });
  };

  const handleConfigSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleCloseConfigModal = () => {
    setConfigModalSession(null);
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

      {configModalSession && (
        <SessionConfigModal
          isOpen={!!configModalSession}
          onClose={handleCloseConfigModal}
          sessionId={configModalSession.id}
          sessionPhone={configModalSession.phone}
          onSuccess={handleConfigSuccess}
        />
      )}
    </AppLayout>
  );
};

export default SessionsPage;
