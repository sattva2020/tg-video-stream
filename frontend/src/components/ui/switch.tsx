import * as React from 'react';
import { cn } from '../../lib/utils';

export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(({ className, checked, onCheckedChange, ...props }, ref) => (
  <label className="inline-flex items-center cursor-pointer">
    <input
      ref={ref}
      type="checkbox"
      className="sr-only"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      {...props}
    />
    <span
      className={cn(
        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
        checked ? 'bg-[color:var(--color-accent)]' : 'bg-[color:var(--color-border)]',
        className,
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform',
          checked ? 'translate-x-4' : 'translate-x-0.5'
        )}
      />
    </span>
  </label>
));
Switch.displayName = 'Switch';
