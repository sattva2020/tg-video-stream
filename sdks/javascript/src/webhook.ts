/**
 * Webhook signature verification utilities
 */

/**
 * Convert string to ArrayBuffer
 */
function stringToArrayBuffer(str: string): ArrayBuffer {
  const encoder = new TextEncoder();
  return encoder.encode(str).buffer;
}

/**
 * Convert ArrayBuffer to hex string
 */
function arrayBufferToHex(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Verify webhook signature using HMAC-SHA256
 * @param payload - The webhook payload (object or string)
 * @param signature - The signature from X-Webhook-Signature header
 * @param secret - The webhook secret
 * @returns True if signature is valid
 */
export async function verifyWebhookSignature(
  payload: string | Record<string, any>,
  signature: string,
  secret: string
): Promise<boolean> {
  // Convert payload to string if it's an object
  const payloadString =
    typeof payload === 'string' ? payload : JSON.stringify(payload);

  // Extract signature (remove 'sha256=' prefix if present)
  const signatureHash = signature.startsWith('sha256=')
    ? signature.substring(7)
    : signature;

  // Generate expected signature using Web Crypto API
  const keyData = stringToArrayBuffer(secret);
  const messageData = stringToArrayBuffer(payloadString);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );

  const signatureBytes = new Uint8Array(
    signatureHash.match(/.{1,2}/g)?.map((byte) => parseInt(byte, 16)) || []
  );

  const isValid = await crypto.subtle.verify(
    'HMAC',
    cryptoKey,
    signatureBytes,
    messageData
  );

  return isValid;
}

/**
 * Generate a webhook signature (for testing purposes)
 * @param payload - The webhook payload
 * @param secret - The webhook secret
 * @returns The signature in format 'sha256=<hex>'
 */
export async function generateWebhookSignature(
  payload: string | Record<string, any>,
  secret: string
): Promise<string> {
  const payloadString =
    typeof payload === 'string' ? payload : JSON.stringify(payload);

  const keyData = stringToArrayBuffer(secret);
  const messageData = stringToArrayBuffer(payloadString);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBuffer = await crypto.subtle.sign(
    'HMAC',
    cryptoKey,
    messageData
  );

  const signature = arrayBufferToHex(signatureBuffer);
  return `sha256=${signature}`;
}
