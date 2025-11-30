export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin',
  MODERATOR = 'moderator',
  OPERATOR = 'operator',
}

export interface User {
  id: string;
  email?: string;
  full_name?: string;
  profile_picture_url?: string;
  role: UserRole;
  status?: string;
  google_id?: string;
  telegram_id?: number;
  telegram_username?: string;
}
