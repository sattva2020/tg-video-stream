/**
 * Webhook signature verification utilities
 */

import * as crypto from 'crypto';

/**
 * Verify webhook signature using HMAC-SHA256
 * @param payload - The webhook payload (object or string)
 * @param signature - The signature from X-Webhook-Signature header
 * @param secret - The webhook secret
 * @returns True if signature is valid
 */
export function verifyWebhookSignature(
  payload: string | Record<string, any>,
  signature: string,
  secret: string
): boolean {
  // Convert payload to string if it's an object
  const payloadString =
    typeof payload === 'string' ? payload : JSON.stringify(payload);

  // Extract signature (remove 'sha256=' prefix if present)
  const signatureHash = signature.startsWith('sha256=')
    ? signature.substring(7)
    : signature;

  // Generate expected signature
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(payloadString);
  const expectedSignature = hmac.digest('hex');

  // Constant-time comparison to prevent timing attacks
  return timingSafeEqual(
    Buffer.from(signatureHash, 'hex'),
    Buffer.from(expectedSignature, 'hex')
  );
}

/**
 * Constant-time comparison to prevent timing attacks
 */
function timingSafeEqual(a: Buffer, b: Buffer): boolean {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a[i] ^ b[i];
  }

  return result === 0;
}

/**
 * Generate a webhook signature (for testing purposes)
 * @param payload - The webhook payload
 * @param secret - The webhook secret
 * @returns The signature in format 'sha256=<hex>'
 */
export function generateWebhookSignature(
  payload: string | Record<string, any>,
  secret: string
): string {
  const payloadString =
    typeof payload === 'string' ? payload : JSON.stringify(payload);

  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(payloadString);
  const signature = hmac.digest('hex');

  return `sha256=${signature}`;
}
