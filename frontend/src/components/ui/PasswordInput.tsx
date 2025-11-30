import React, { useState, forwardRef } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Custom class for the wrapper div */
  wrapperClassName?: string;
  /** Custom class for the toggle button */
  buttonClassName?: string;
  /** Icon size in pixels */
  iconSize?: number;
}

/**
 * Password input with show/hide toggle
 * 
 * @example
 * <PasswordInput
 *   id="password"
 *   placeholder="Enter password"
 *   {...register('password')}
 * />
 */
export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, wrapperClassName, buttonClassName, iconSize = 18, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    const toggleVisibility = () => {
      setShowPassword((prev) => !prev);
    };

    return (
      <div className={`relative ${wrapperClassName || ''}`}>
        <input
          ref={ref}
          type={showPassword ? 'text' : 'password'}
          className={className}
          {...props}
        />
        <button
          type="button"
          onClick={toggleVisibility}
          className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 text-current opacity-50 hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-current focus-visible:ring-offset-1 rounded ${buttonClassName || ''}`}
          tabIndex={-1}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <EyeOff size={iconSize} aria-hidden="true" />
          ) : (
            <Eye size={iconSize} aria-hidden="true" />
          )}
        </button>
      </div>
    );
  }
);

PasswordInput.displayName = 'PasswordInput';

export default PasswordInput;
