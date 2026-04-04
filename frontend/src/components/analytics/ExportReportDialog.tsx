/**
 * ExportReportDialog Component
 * Feature: 012-comprehensive-analytics-dashboard
 *
 * Dialog for exporting analytics data as CSV and scheduling reports.
 */

import React, { useState, useCallback } from 'react';
import {
  Download,
  Calendar,
  FileSpreadsheet,
  Clock,
  Check,
  X,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/Dialog';
import { motion } from 'framer-motion';

interface ExportReportDialogProps {
  onExport?: (options: ExportOptions) => Promise<void>;
  onSchedule?: (options: ScheduleOptions) => Promise<void>;
  trigger?: React.ReactNode;
}

export interface ExportOptions {
  format: 'csv';
  dateRange: '7d' | '30d' | '90d' | 'custom';
  includeMetrics: string[];
}

export interface ScheduleOptions {
  frequency: 'daily' | 'weekly' | 'monthly';
  email: string;
  includeMetrics: string[];
}

const AVAILABLE_METRICS = [
  { id: 'listeners', label: 'Listeners' },
  { id: 'views', label: 'Views' },
  { id: 'engagement', label: 'Engagement Rate' },
  { id: 'retention', label: 'Retention' },
  { id: 'topTracks', label: 'Top Tracks' },
  { id: 'streamPerformance', label: 'Stream Performance' },
];

const DATE_RANGES = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
];

const FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

type Tab = 'export' | 'schedule';

export const ExportReportDialog: React.FC<ExportReportDialogProps> = ({
  onExport,
  onSchedule,
  trigger,
}) => {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('export');
  const [isExporting, setIsExporting] = useState(false);
  const [isScheduling, setIsScheduling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Export form state
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'csv',
    dateRange: '30d',
    includeMetrics: ['listeners', 'views', 'engagement'],
  });

  // Schedule form state
  const [scheduleOptions, setScheduleOptions] = useState<ScheduleOptions>({
    frequency: 'weekly',
    email: '',
    includeMetrics: ['listeners', 'views', 'engagement'],
  });

  const toggleMetric = useCallback((metricId: string, tab: Tab) => {
    const setter = tab === 'export' ? setExportOptions : setScheduleOptions;
    setter((prev) => ({
      ...prev,
      includeMetrics: prev.includeMetrics.includes(metricId)
        ? prev.includeMetrics.filter((m) => m !== metricId)
        : [...prev.includeMetrics, metricId],
    }));
  }, []);

  const handleExport = useCallback(async () => {
    if (exportOptions.includeMetrics.length === 0) {
      setError('Please select at least one metric');
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      if (onExport) {
        await onExport(exportOptions);
      } else {
        // Default export behavior - generate CSV
        const csv = generateMockCSV(exportOptions);
        downloadCSV(csv, `analytics-export-${exportOptions.dateRange}.csv`);
      }
      setSuccess(true);
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  }, [exportOptions, onExport]);

  const handleSchedule = useCallback(async () => {
    if (!scheduleOptions.email.trim()) {
      setError('Please enter an email address');
      return;
    }

    if (!scheduleOptions.email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    if (scheduleOptions.includeMetrics.length === 0) {
      setError('Please select at least one metric');
      return;
    }

    setIsScheduling(true);
    setError(null);

    try {
      if (onSchedule) {
        await onSchedule(scheduleOptions);
      } else {
        // Default schedule behavior
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      setSuccess(true);
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        setScheduleOptions((prev) => ({ ...prev, email: '' }));
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scheduling failed');
    } finally {
      setIsScheduling(false);
    }
  }, [scheduleOptions, onSchedule]);

  const handleClose = useCallback(() => {
    setOpen(false);
    setError(null);
    setSuccess(false);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-500/10">
              {activeTab === 'export' ? (
                <FileSpreadsheet className="w-5 h-5 text-violet-600 dark:text-violet-400" />
              ) : (
                <Calendar className="w-5 h-5 text-violet-600 dark:text-violet-400" />
              )}
            </div>
            <div>
              <DialogTitle>
                {activeTab === 'export' ? 'Export Analytics' : 'Schedule Reports'}
              </DialogTitle>
              <DialogDescription>
                {activeTab === 'export'
                  ? 'Download your analytics data as CSV'
                  : 'Automatically receive reports via email'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex gap-2 p-1 rounded-lg bg-[color:var(--color-surface)]">
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab('export')}
            className={`
              flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
              ${activeTab === 'export'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-white/5'
              }
            `}
          >
            <Download className="w-4 h-4" />
            Export
          </motion.button>
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab('schedule')}
            className={`
              flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
              ${activeTab === 'schedule'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-white/5'
              }
            `}
          >
            <Calendar className="w-4 h-4" />
            Schedule
          </motion.button>
        </div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20"
          >
            <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
          </motion.div>
        )}

        {/* Success Message */}
        {success && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20"
          >
            <p className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <Check className="w-4 h-4" />
              {activeTab === 'export' ? 'Export started!' : 'Report scheduled!'}
            </p>
          </motion.div>
        )}

        {/* Export Tab Content */}
        {activeTab === 'export' && (
          <div className="space-y-4">
            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                Date Range
              </label>
              <div className="flex flex-wrap gap-2">
                {DATE_RANGES.map((range) => (
                  <motion.button
                    key={range.value}
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    onClick={() =>
                      setExportOptions((prev) => ({ ...prev, dateRange: range.value as any }))
                    }
                    className={`
                      px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                      ${exportOptions.dateRange === range.value
                        ? 'bg-violet-600 text-white'
                        : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:bg-white/5'
                      }
                    `}
                  >
                    {range.label}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Metrics Selection */}
            <div>
              <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                Include Metrics
              </label>
              <div className="space-y-2">
                {AVAILABLE_METRICS.map((metric) => (
                  <motion.label
                    key={metric.id}
                    whileTap={{ scale: 0.99 }}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all
                      ${exportOptions.includeMetrics.includes(metric.id)
                        ? 'bg-violet-500/10 border border-violet-500/20'
                        : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                      }
                    `}
                  >
                    <input
                      type="checkbox"
                      checked={exportOptions.includeMetrics.includes(metric.id)}
                      onChange={() => toggleMetric(metric.id, 'export')}
                      className="w-4 h-4 rounded border-[color:var(--color-border)] text-violet-600 focus:ring-violet-500 focus:ring-offset-0"
                    />
                    <span className="text-sm text-[color:var(--color-text)]">{metric.label}</span>
                  </motion.label>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Schedule Tab Content */}
        {activeTab === 'schedule' && (
          <div className="space-y-4">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={scheduleOptions.email}
                onChange={(e) =>
                  setScheduleOptions((prev) => ({ ...prev, email: e.target.value }))
                }
                placeholder="your@email.com"
                className="w-full px-3 py-2 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-[color:var(--color-text)] placeholder:text-[color:var(--color-text-muted)] focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              />
            </div>

            {/* Frequency */}
            <div>
              <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                Frequency
              </label>
              <div className="flex gap-2">
                {FREQUENCIES.map((freq) => (
                  <motion.button
                    key={freq.value}
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    onClick={() =>
                      setScheduleOptions((prev) => ({
                        ...prev,
                        frequency: freq.value as any,
                      }))
                    }
                    className={`
                      flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all
                      ${scheduleOptions.frequency === freq.value
                        ? 'bg-violet-600 text-white'
                        : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:bg-white/5'
                      }
                    `}
                  >
                    {freq.label}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Metrics Selection */}
            <div>
              <label className="block text-sm font-medium text-[color:var(--color-text)] mb-2">
                Include Metrics
              </label>
              <div className="space-y-2">
                {AVAILABLE_METRICS.map((metric) => (
                  <motion.label
                    key={metric.id}
                    whileTap={{ scale: 0.99 }}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all
                      ${scheduleOptions.includeMetrics.includes(metric.id)
                        ? 'bg-violet-500/10 border border-violet-500/20'
                        : 'bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:bg-white/5'
                      }
                    `}
                  >
                    <input
                      type="checkbox"
                      checked={scheduleOptions.includeMetrics.includes(metric.id)}
                      onChange={() => toggleMetric(metric.id, 'schedule')}
                      className="w-4 h-4 rounded border-[color:var(--color-border)] text-violet-600 focus:ring-violet-500 focus:ring-offset-0"
                    />
                    <span className="text-sm text-[color:var(--color-text)]">{metric.label}</span>
                  </motion.label>
                ))}
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <button
            type="button"
            onClick={handleClose}
            disabled={isExporting || isScheduling}
            className="px-4 py-2 rounded-lg text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          {activeTab === 'export' ? (
            <button
              type="button"
              onClick={handleExport}
              disabled={isExporting || isScheduling}
              className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isExporting ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Export CSV
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSchedule}
              disabled={isExporting || isScheduling}
              className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isScheduling ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  Scheduling...
                </>
              ) : (
                <>
                  <Calendar className="w-4 h-4" />
                  Schedule Report
                </>
              )}
            </button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Helper function to generate mock CSV data
function generateMockCSV(options: ExportOptions): string {
  const headers = ['Date', ...options.includeMetrics];
  const rows: string[][] = [];

  // Generate mock data for the last 30 days
  const days = options.dateRange === '7d' ? 7 : options.dateRange === '30d' ? 30 : 90;
  for (let i = days; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];

    const row = [dateStr];
    options.includeMetrics.forEach(() => {
      row.push(Math.floor(Math.random() * 1000).toString());
    });
    rows.push(row);
  }

  return [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
}

// Helper function to download CSV
function downloadCSV(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default ExportReportDialog;
