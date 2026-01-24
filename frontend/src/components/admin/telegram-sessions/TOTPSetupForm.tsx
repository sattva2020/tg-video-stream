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
import { telegramApi, TOTPSetupResponse } from '@/api/telegram';
import { useToast } from '@/components/ui/use-toast';
import { QRCodeSVG } from 'qrcode.react';
import { Shield, Smartphone, CheckCircle2, AlertCircle } from 'lucide-react';

interface TOTPSetupFormProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  sessionPhone?: string;
  onSuccess?: () => void;
}

type SetupStep = 'setup' | 'verify';

export const TOTPSetupForm: React.FC<TOTPSetupFormProps> = ({
  isOpen,
  onClose,
  sessionId,
  sessionPhone,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [step, setStep] = useState<SetupStep>('setup');
  const [totpData, setTotpData] = useState<TOTPSetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep('setup');
      setTotpData(null);
      setVerificationCode('');
      setError(null);
      setupTOTP();
    }
  }, [isOpen, sessionId]);

  const setupTOTP = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await telegramApi.setup2FA(sessionId);
      setTotpData(data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to setup 2FA';
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

  const handleVerifyCode = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    // Validation: code must be 6 digits
    if (!verificationCode || !/^\d{6}$/.test(verificationCode)) {
      setError('Please enter a valid 6-digit verification code');
      return;
    }

    setIsVerifying(true);
    try {
      await telegramApi.verify2FA(sessionId, verificationCode);

      toast({
        title: 'Success',
        description: '2FA has been successfully enabled for this session',
      });

      onSuccess?.();
      onClose();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to verify code';
      setError(errorMessage);
      toast({
        title: 'Verification Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCodeChange = (value: string) => {
    // Only allow digits, max 6 characters
    const cleaned = value.replace(/\D/g, '').slice(0, 6);
    setVerificationCode(cleaned);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle data-testid="totp-modal-title">
            {t('setup_2fa_title', 'Setup Two-Factor Authentication')}
          </DialogTitle>
          <DialogDescription data-testid="totp-modal-description">
            {sessionPhone
              ? t('setup_2fa_description_with_phone', 'Enable 2FA for automatic session refresh on {{phone}}', { phone: sessionPhone })
              : t('setup_2fa_description', 'Enable two-factor authentication for automatic session refresh')
            }
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <div className="text-center text-sm text-muted-foreground">
                {t('generating_secret', 'Generating secure secret...')}
              </div>
            </div>
          </div>
        ) : step === 'setup' && totpData ? (
          <div className="space-y-4 py-4">
            {/* Instructions */}
            <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
              <div className="flex items-start gap-3">
                <Smartphone className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-900">
                  <p className="font-medium mb-1">
                    {t('install_authenticator_app', 'Install an authenticator app')}
                  </p>
                  <p className="text-blue-700">
                    {t('install_authenticator_description', 'Use Google Authenticator, Authy, or any TOTP-compatible app')}
                  </p>
                </div>
              </div>
            </div>

            {/* QR Code */}
            <div className="flex flex-col items-center gap-4 p-6 rounded-lg border border-border bg-muted/30">
              <div className="rounded-lg bg-white p-4 shadow-sm">
                {totpData.otpauth_url && (
                  <QRCodeSVG
                    value={totpData.otpauth_url}
                    size={200}
                    level="M"
                    includeMargin={false}
                    data-testid="totp-qr-code"
                  />
                )}
              </div>
              <p className="text-xs text-center text-muted-foreground max-w-[300px]">
                {t('scan_qr_code', 'Scan this QR code with your authenticator app')}
              </p>
            </div>

            {/* Secret (for manual entry) */}
            <div className="rounded-lg bg-muted/50 p-3">
              <Label htmlFor="totp-secret" className="text-xs font-medium">
                {t('or_enter_manually', 'Or enter this code manually:')}
              </Label>
              <div className="mt-2 flex items-center gap-2">
                <code
                  id="totp-secret"
                  className="flex-1 text-center font-mono text-sm bg-background border border-border rounded px-3 py-2 select-all"
                  data-testid="totp-secret"
                >
                  {totpData.secret}
                </code>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive flex items-start gap-2" role="alert">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                data-testid="cancel-button"
              >
                {t('cancel', 'Cancel')}
              </Button>
              <Button
                type="button"
                onClick={() => setStep('verify')}
                data-testid="continue-button"
              >
                {t('continue', 'Continue')}
              </Button>
            </DialogFooter>
          </div>
        ) : step === 'verify' ? (
          <form onSubmit={handleVerifyCode}>
            <div className="space-y-4 py-4">
              {/* Instructions */}
              <div className="rounded-lg bg-green-50 border border-green-200 p-4">
                <div className="flex items-start gap-3">
                  <Shield className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-green-900">
                    <p className="font-medium mb-1">
                      {t('enter_verification_code', 'Enter verification code')}
                    </p>
                    <p className="text-green-700">
                      {t('enter_verification_code_description', 'Enter the 6-digit code from your authenticator app')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Verification code input */}
              <div className="space-y-2">
                <Label htmlFor="verification-code">
                  {t('verification_code', 'Verification Code')}
                </Label>
                <Input
                  id="verification-code"
                  type="text"
                  inputMode="numeric"
                  pattern="\d{6}"
                  maxLength={6}
                  placeholder="000000"
                  value={verificationCode}
                  onChange={(e) => handleCodeChange(e.target.value)}
                  disabled={isVerifying}
                  className="text-center text-lg tracking-[0.5em] font-mono"
                  autoFocus
                  data-testid="verification-code-input"
                />
                <p className="text-xs text-center text-muted-foreground">
                  {t('enter_6_digit_code', 'Enter the 6-digit code from your app')}
                </p>
              </div>

              {/* Success indicator when code is complete */}
              {verificationCode.length === 6 && !error && (
                <div className="flex items-center justify-center gap-2 text-sm text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  {t('code_complete', 'Code entered - ready to verify')}
                </div>
              )}

              {/* Error message */}
              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive flex items-start gap-2" role="alert">
                  <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setStep('setup')}
                  disabled={isVerifying}
                  data-testid="back-button"
                >
                  {t('back', 'Back')}
                </Button>
                <Button
                  type="submit"
                  disabled={verificationCode.length !== 6 || isVerifying}
                  data-testid="verify-button"
                >
                  {isVerifying
                    ? t('verifying', 'Verifying...')
                    : t('verify_and_enable', 'Verify & Enable 2FA')
                  }
                </Button>
              </DialogFooter>
            </div>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
};

export default TOTPSetupForm;
