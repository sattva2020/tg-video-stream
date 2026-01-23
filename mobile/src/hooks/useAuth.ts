/**
 * useAuth hook
 *
 * This hook provides access to the authentication context.
 * It's a convenience export to make imports cleaner and follows the pattern
 * of separating hooks from context definitions.
 *
 * Usage:
 * ```tsx
 * import { useAuth } from '@/hooks/useAuth';
 *
 * const { user, isAuthenticated, login, logout } = useAuth();
 * ```
 */

export { useAuth } from '../contexts/AuthContext';
