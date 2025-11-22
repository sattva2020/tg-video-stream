import { client } from './client';
import { z } from 'zod';
import { User } from '../types/user';

// Zod schemas for validation
export const LoginSchema = z.object({
  username: z.string().email(), // OAuth2PasswordRequestForm uses 'username' for email
  password: z.string().min(1, "Password is required"),
});

export const RegisterSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string()
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one number")
    .regex(/[!@#$%^&*]/, "Password must contain at least one special character (!@#$%^&*)"),
  full_name: z.string().optional(),
});

export const PasswordResetRequestSchema = z.object({
  email: z.string().email("Invalid email address"),
});

export const PasswordResetConfirmSchema = z.object({
  token: z.string().min(1, "Token is required"),
  new_password: z.string()
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one number")
    .regex(/[!@#$%^&*]/, "Password must contain at least one special character (!@#$%^&*)"),
});

export type LoginRequest = z.infer<typeof LoginSchema>;
export type RegisterRequest = z.infer<typeof RegisterSchema>;
export type PasswordResetRequestData = z.infer<typeof PasswordResetRequestSchema>;
export type PasswordResetConfirmData = z.infer<typeof PasswordResetConfirmSchema>;

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  login: async (data: LoginRequest) => {
    // Use JSON { email, password } so backend pydantic model (email,password)
    // validates correctly. The UI login field is named `username` in forms,
    // we map it to `email` here.
    const payload = { email: data.username, password: data.password };
    const response = await client.post<AuthResponse>('/api/auth/login', payload);
    return response.data;
  },

  register: async (data: RegisterRequest) => {
    const response = await client.post('/api/auth/register', data);
    return response.data;
  },

  requestPasswordReset: async (data: PasswordResetRequestData) => {
    const response = await client.post('/api/auth/password-reset/request', data);
    return response.data;
  },

  confirmPasswordReset: async (data: PasswordResetConfirmData) => {
    const response = await client.post('/api/auth/password-reset/confirm', data);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('token');
  },
  
  getMe: async (): Promise<User> => {
    const response = await client.get<User>('/api/users/me');
    return response.data;
  }
};
