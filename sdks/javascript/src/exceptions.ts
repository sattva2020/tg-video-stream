/**
 * Custom error classes for the Sattva API SDK
 */

/**
 * Base error class for all Sattva API errors
 */
export class SattvaAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'SattvaAPIError';
    Object.setPrototypeOf(this, SattvaAPIError.prototype);
  }
}

/**
 * Authentication error (401)
 */
export class AuthenticationError extends SattvaAPIError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Rate limit error (429)
 */
export class RateLimitError extends SattvaAPIError {
  constructor(
    message: string = 'Rate limit exceeded',
    public retryAfter?: number
  ) {
    super(message, 429);
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

/**
 * Not found error (404)
 */
export class NotFoundError extends SattvaAPIError {
  constructor(message: string = 'Resource not found') {
    super(message, 404);
    this.name = 'NotFoundError';
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

/**
 * Validation error (400, 422)
 */
export class ValidationError extends SattvaAPIError {
  constructor(
    message: string = 'Validation failed',
    public errors?: Record<string, string[]>
  ) {
    super(message, 400);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}
