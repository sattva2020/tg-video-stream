/**
 * LogCollectorContext - глобальный контекст для сбора логов
 * 
 * Оборачивает приложение и предоставляет доступ к коллектору логов
 * из любого компонента.
 * 
 * @example
 * // В App.tsx
 * <LogCollectorProvider>
 *   <App />
 * </LogCollectorProvider>
 * 
 * // В любом компоненте
 * const { logAction, createIncident, openReportDialog } = useLogCollectorContext();
 */

import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { useLogCollector, type UseLogCollectorReturn } from '../hooks/useLogCollector';
import ReportIncidentDialog from '../components/ReportIncidentDialog';

interface LogCollectorContextValue extends UseLogCollectorReturn {
  openReportDialog: () => void;
  closeReportDialog: () => void;
  isReportDialogOpen: boolean;
}

const LogCollectorContext = createContext<LogCollectorContextValue | null>(null);

interface LogCollectorProviderProps {
  children: ReactNode;
  enabled?: boolean;
}

export function LogCollectorProvider({ children, enabled = true }: LogCollectorProviderProps) {
  const collector = useLogCollector({ enabled });
  const [isReportDialogOpen, setIsReportDialogOpen] = useState(false);

  const openReportDialog = useCallback(() => {
    setIsReportDialogOpen(true);
  }, []);

  const closeReportDialog = useCallback(() => {
    setIsReportDialogOpen(false);
  }, []);

  const value: LogCollectorContextValue = {
    ...collector,
    openReportDialog,
    closeReportDialog,
    isReportDialogOpen,
  };

  return (
    <LogCollectorContext.Provider value={value}>
      {children}
      <ReportIncidentDialog 
        isOpen={isReportDialogOpen} 
        onClose={closeReportDialog}
        logs={collector.logs}
        browserInfo={collector.browserInfo}
        lastError={collector.lastError}
      />
    </LogCollectorContext.Provider>
  );
}

export function useLogCollectorContext(): LogCollectorContextValue {
  const context = useContext(LogCollectorContext);
  if (!context) {
    throw new Error('useLogCollectorContext must be used within a LogCollectorProvider');
  }
  return context;
}

export default LogCollectorContext;
