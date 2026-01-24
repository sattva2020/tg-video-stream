import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Switch } from '@/components/ui/Switch';
import { telegramApi, SessionConfig } from '@/api/telegram';
import { useToast } from '@/components/ui/use-toast';

interface SessionConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  sessionPhone?: string;
  onSuccess?: () => void;
}

export const SessionConfigModal: React.FC<SessionConfigModalProps> = ({
  isOpen,
  onClose,
  sessionId,
  sessionPhone,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [config, setConfig] = useState<{
    auto_refresh_enabled: boolean;
    refresh_before_expires_hours: number;
  }>({
    auto_refresh_enabled: false,
    refresh_before_expires_hours: 24,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Загрузка текущей конфигурации при открытии модального окна
  useEffect(() => {
    if (isOpen && sessionId) {
      fetchConfig();
    }
  }, [isOpen, sessionId]);

  const fetchConfig = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await telegramApi.getSessionConfig(sessionId);
      setConfig({
        auto_refresh_enabled: data.auto_refresh_enabled,
        refresh_before_expires_hours: data.refresh_before_expires_hours,
      });
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch session configuration';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    // Валидация
    if (config.auto_refresh_enabled) {
      if (config.refresh_before_expires_hours < 1 || config.refresh_before_expires_hours > 168) {
        setError('Refresh hours must be between 1 and 168');
        return;
      }
    }

    setIsSaving(true);
    try {
      await telegramApi.updateSessionConfig(sessionId, {
        auto_refresh_enabled: config.auto_refresh_enabled,
        refresh_before_expires_hours: config.refresh_before_expires_hours,
      });

      toast({
        title: 'Success',
        description: 'Session configuration updated successfully',
      });

      onSuccess?.();
      onClose();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to update session configuration';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleHoursChange = (value: string) => {
    const hours = parseInt(value, 10);
    if (!isNaN(hours) && hours >= 0 && hours <= 168) {
      setConfig({ ...config, refresh_before_expires_hours: hours });
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle data-testid="config-modal-title">
            {t('session_config_title', 'Session Configuration')}
          </DialogTitle>
          <DialogDescription data-testid="config-modal-description">
            {sessionPhone
              ? t('session_config_description_with_phone', 'Configure auto-refresh settings for {{phone}}', { phone: sessionPhone })
              : t('session_config_description', 'Configure auto-refresh and rotation settings for this Telegram session')
            }
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-6">
            <div className="text-center text-sm text-muted-foreground">
              {t('loading_config', 'Loading configuration...')}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              {/* Auto-refresh toggle */}
              <div className="flex items-center justify-between space-x-2">
                <Label htmlFor="auto-refresh" className="flex-1">
                  {t('auto_refresh_enabled', 'Enable Auto-refresh')}
                </Label>
                <Switch
                  id="auto-refresh"
                  checked={config.auto_refresh_enabled}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, auto_refresh_enabled: checked })
                  }
                  disabled={isSaving}
                  data-testid="auto-refresh-switch"
                />
              </div>

              <p className="text-xs text-muted-foreground">
                {t('auto_refresh_description', 'Automatically refresh the session before it expires to maintain continuous operation')}
              </p>

              {/* Refresh before expires hours */}
              <div className="space-y-2">
                <Label htmlFor="refresh-hours">
                  {t('refresh_before_expires_hours', 'Refresh Before Expires (hours)')}
                </Label>
                <Input
                  id="refresh-hours"
                  type="number"
                  min={1}
                  max={168}
                  step={1}
                  value={config.refresh_before_expires_hours}
                  onChange={(e) => handleHoursChange(e.target.value)}
                  disabled={isSaving || !config.auto_refresh_enabled}
                  data-testid="refresh-hours-input"
                />
                <p className="text-xs text-muted-foreground">
                  {t('refresh_hours_description', 'How many hours before expiration to refresh the session (1-168 hours)')}
                </p>
              </div>

              {/* Error message */}
              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
                  {error}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSaving}
                data-testid="cancel-button"
              >
                {t('cancel', 'Cancel')}
              </Button>
              <Button
                type="submit"
                disabled={isSaving || isLoading}
                data-testid="save-button"
              >
                {isSaving
                  ? t('saving', 'Saving...')
                  : t('save_changes', 'Save Changes')
                }
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default SessionConfigModal;
