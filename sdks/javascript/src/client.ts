/**
 * Base HTTP client for Sattva API
 */

import type { SattvaClientConfig } from './types';
import {
  SattvaAPIError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ValidationError,
} from './exceptions';

export class SattvaClient {
  private config: Required<SattvaClientConfig>;

  constructor(config: SattvaClientConfig) {
    this.config = {
      apiKey: config.apiKey,
      baseUrl: config.baseUrl || 'https://api.sattva-streamer.top/api/v1',
      timeout: config.timeout || 30000,
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
    };
  }

  /**
   * Make an HTTP request to the API
   */
  private async request<T>(
    method: string,
    path: string,
    body?: any,
    retries = 0
  ): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const headers: HeadersInit = {
      'X-API-Key': this.config.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        this.config.timeout
      );

      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle rate limiting with automatic retry
      if (response.status === 429 && retries < this.config.maxRetries) {
        const retryAfter = response.headers.get('Retry-After');
        const delay = retryAfter
          ? parseInt(retryAfter) * 1000
          : this.config.retryDelay * Math.pow(2, retries);

        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.request<T>(method, path, body, retries + 1);
      }

      // Handle error responses
      if (!response.ok) {
        await this.handleError(response);
      }

      // Return successful response
      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof SattvaAPIError) {
        throw error;
      }
      throw new SattvaAPIError(
        `Request failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Handle error responses from the API
   */
  private async handleError(response: Response): Promise<never> {
    const status = response.status;
    let message = 'API request failed';
    let errorDetail: any;

    try {
      errorDetail = await response.json();
      message = errorDetail.message || errorDetail.detail || message;
    } catch {
      message = response.statusText || message;
    }

    switch (status) {
      case 401:
      case 403:
        throw new AuthenticationError(message);
      case 404:
        throw new NotFoundError(message);
      case 429:
        const retryAfter = response.headers.get('Retry-After');
        throw new RateLimitError(message, retryAfter ? parseInt(retryAfter) : undefined);
      case 400:
      case 422:
        throw new ValidationError(message, errorDetail?.errors);
      default:
        throw new SattvaAPIError(message, status, errorDetail);
    }
  }

  /**
   * Make a GET request
   */
  protected async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  /**
   * Make a POST request
   */
  protected async post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  /**
   * Make a PATCH request
   */
  protected async patch<T>(path: string, body?: any): Promise<T> {
    return this.request<T>('PATCH', path, body);
  }

  /**
   * Make a DELETE request
   */
  protected async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  /**
   * Make a PUT request
   */
  protected async put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>('PUT', path, body);
  }
}
