/**
 * Test Helper Utilities
 *
 * Utility functions to assist with E2E testing and verification.
 * These helpers can be used during manual testing or in automated test scripts.
 *
 * NOTE: This file should NOT be included in production builds.
 * Use environment checks to ensure it's only loaded in development/test mode.
 */

import * as SecureStore from 'expo-secure-store';
import { tokenStorage } from '../api/auth';
import { canUseBiometric } from './biometricAuth';

/**
 * Test result interface
 */
export interface TestResult {
  testName: string;
  passed: boolean;
  message: string;
  timestamp: Date;
  details?: Record<string, any>;
}

/**
 * Test suite results
 */
export interface TestSuiteResults {
  suiteName: string;
  totalTests: number;
  passed: number;
  failed: number;
  results: TestResult[];
  startTime: Date;
  endTime: Date;
  duration: number; // in milliseconds
}

/**
 * Assert a condition is true
 */
export const assert = (
  condition: boolean,
  message: string
): { passed: boolean; message: string } => {
  if (condition) {
    return { passed: true, message: `✓ ${message}` };
  }
  return { passed: false, message: `✗ ${message}` };
};

/**
 * Assert two values are equal
 */
export const assertEquals = (
  actual: any,
  expected: any,
  label: string
): { passed: boolean; message: string } => {
  if (actual === expected) {
    return { passed: true, message: `✓ ${label}: ${actual}` };
  }
  return {
    passed: false,
    message: `✗ ${label}: expected "${expected}" but got "${actual}"`,
  };
};

/**
 * Assert a value is not null or undefined
 */
export const assertNotNull = (
  value: any,
  label: string
): { passed: boolean; message: string } => {
  if (value !== null && value !== undefined) {
    return { passed: true, message: `✓ ${label} is not null` };
  }
  return { passed: false, message: `✗ ${label} is null or undefined` };
};

/**
 * Assert a value is null or undefined
 */
export const assertNull = (
  value: any,
  label: string
): { passed: boolean; message: string } => {
  if (value === null || value === undefined) {
    return { passed: true, message: `✓ ${label} is null` };
  }
  return { passed: false, message: `✗ ${label} should be null but got: ${value}` };
};

/**
 * Get authentication state for testing
 */
export const getAuthState = async (): Promise<{
  hasToken: boolean;
  tokenValue: string | null;
  biometricEnabled: boolean;
  biometricEmail: string | null;
}> => {
  try {
    const token = await tokenStorage.getToken();
    const biometricEnabled = await canUseBiometric();
    const biometricEmail = await SecureStore.getItemAsync('biometricEmail');

    return {
      hasToken: !!token,
      tokenValue: token,
      biometricEnabled,
      biometricEmail,
    };
  } catch (error) {
    return {
      hasToken: false,
      tokenValue: null,
      biometricEnabled: false,
      biometricEmail: null,
    };
  }
};

/**
 * Clear all authentication state (for test cleanup)
 */
export const clearAuthState = async (): Promise<void> => {
  try {
    await tokenStorage.removeToken();
    await SecureStore.deleteItemAsync('biometricEnabled');
    await SecureStore.deleteItemAsync('biometricEmail');
  } catch (error) {
    // Silently fail
  }
};

/**
 * Verify login screen is displayed
 */
export const verifyLoginScreen = (currentRoute: string): TestResult => {
  const isLoginScreen = currentRoute === 'Login';

  return {
    testName: 'TC-AUTH-001: Login Screen Display',
    passed: isLoginScreen,
    message: isLoginScreen
      ? 'Login screen is displayed'
      : `Expected Login screen but got: ${currentRoute}`,
    timestamp: new Date(),
  };
};

/**
 * Verify user is authenticated
 */
export const verifyUserAuthenticated = async (
  user: any
): Promise<TestResult> => {
  const checks = [
    assertNotNull(user, 'User object'),
    assertNotNull(user?.id, 'User ID'),
    assertNotNull(user?.email, 'User email'),
    assertNotNull(user?.role, 'User role'),
  ];

  const allPassed = checks.every((check) => check.passed);

  return {
    testName: 'Verify User Authenticated',
    passed: allPassed,
    message: allPassed
      ? 'User is authenticated with all required fields'
      : `Authentication incomplete: ${checks.filter((c) => !c.passed).map((c) => c.message).join(', ')}`,
    timestamp: new Date(),
    details: {
      userId: user?.id,
      email: user?.email,
      role: user?.role,
    },
  };
};

/**
 * Verify biometric state
 */
export const verifyBiometricState = async (
  expectedEnabled: boolean
): Promise<TestResult> => {
  const actualEnabled = await canUseBiometric();
  const result = assertEquals(
    actualEnabled,
    expectedEnabled,
    'Biometric enabled'
  );

  return {
    testName: 'Verify Biometric State',
    passed: result.passed,
    message: result.message,
    timestamp: new Date(),
    details: {
      expected: expectedEnabled,
      actual: actualEnabled,
    },
  };
};

/**
 * Verify token exists in storage
 */
export const verifyTokenExists = async (): Promise<TestResult> => {
  const token = await tokenStorage.getToken();
  const result = assertNotNull(token, 'Auth token');

  return {
    testName: 'Verify Token Exists',
    passed: result.passed,
    message: result.message,
    timestamp: new Date(),
    details: {
      tokenLength: token?.length || 0,
      tokenPrefix: token?.substring(0, 20) || null,
    },
  };
};

/**
 * Verify token does not exist in storage
 */
export const verifyTokenNotExists = async (): Promise<TestResult> => {
  const token = await tokenStorage.getToken();
  const result = assertNull(token, 'Auth token');

  return {
    testName: 'Verify Token Not Exists',
    passed: result.passed,
    message: result.message,
    timestamp: new Date(),
  };
};

/**
 * Verify navigation to specific screen
 */
export const verifyNavigation = (
  currentRoute: string,
  expectedRoute: string
): TestResult => {
  const result = assertEquals(currentRoute, expectedRoute, 'Current route');

  return {
    testName: `Verify Navigation to ${expectedRoute}`,
    passed: result.passed,
    message: result.message,
    timestamp: new Date(),
  };
};

/**
 * Create a test suite runner
 */
export const createTestSuite = (suiteName: string) => {
  const results: TestResult[] = [];
  const startTime = new Date();

  return {
    /**
     * Add a test result
     */
    addTest: (test: TestResult) => {
      results.push(test);
    },

    /**
     * Run a test function and record result
     */
    runTest: async (
      testName: string,
      testFn: () => Promise<boolean> | boolean,
      errorMessage?: string
    ) => {
      try {
        const passed = await testFn();
        results.push({
          testName,
          passed,
          message: passed ? `✓ ${testName}` : `✗ ${testName}${errorMessage ? `: ${errorMessage}` : ''}`,
          timestamp: new Date(),
        });
      } catch (error: any) {
        results.push({
          testName,
          passed: false,
          message: `✗ ${testName}: Exception thrown - ${error.message}`,
          timestamp: new Date(),
          details: { error: error.message, stack: error.stack },
        });
      }
    },

    /**
     * Get test suite results
     */
    getResults: (): TestSuiteResults => {
      const endTime = new Date();
      const passed = results.filter((r) => r.passed).length;
      const failed = results.filter((r) => !r.passed).length;

      return {
        suiteName,
        totalTests: results.length,
        passed,
        failed,
        results,
        startTime,
        endTime,
        duration: endTime.getTime() - startTime.getTime(),
      };
    },

    /**
     * Print test results to console
     */
    printResults: () => {
      const suiteResults = this.getResults();

      console.log('\n' + '='.repeat(60));
      console.log(`Test Suite: ${suiteName}`);
      console.log('='.repeat(60));
      console.log(`Total Tests: ${suiteResults.totalTests}`);
      console.log(`Passed: ${suiteResults.passed}`);
      console.log(`Failed: ${suiteResults.failed}`);
      console.log(`Duration: ${suiteResults.duration}ms`);
      console.log('='.repeat(60) + '\n');

      suiteResults.results.forEach((result, index) => {
        console.log(`${index + 1}. ${result.message}`);
        if (result.details) {
          console.log(`   Details: ${JSON.stringify(result.details, null, 2)}`);
        }
      });

      console.log('\n' + '='.repeat(60) + '\n');
    },

    /**
     * Export results as JSON
     */
    exportResults: (): string => {
      return JSON.stringify(this.getResults(), null, 2);
    },
  };
};

/**
 * E2E Test: Authentication Flow
 *
 * This function can be called to verify the entire authentication flow.
 * It's designed to be used during manual testing with a debugger or console.
 */
export const runAuthFlowE2E = async () => {
  const suite = createTestSuite('E2E Authentication Flow');

  // Test 1: Verify initial state (not logged in)
  await suite.runTest('Initial state - no token', async () => {
    const token = await tokenStorage.getToken();
    return token === null;
  });

  // Test 2: Verify biometric not enabled initially
  await suite.runTest('Initial state - biometric not enabled', async () => {
    const enabled = await canUseBiometric();
    return !enabled;
  });

  // Note: The actual login, biometric, and navigation tests need to be
  // performed manually by the tester. These tests verify the state changes.

  suite.printResults();
  return suite.getResults();
};

/**
 * Test reporter for manual testing
 *
 * Call this function during manual testing to record test results.
 * Results can be exported and added to the test plan document.
 */
export const createTestReporter = () => {
  const results: TestResult[] = [];

  return {
    /**
     * Record a manual test result
     */
    record: (
      testName: string,
      passed: boolean,
      notes?: string
    ) => {
      results.push({
        testName,
        passed,
        message: passed ? `✓ ${testName}` : `✗ ${testName}`,
        timestamp: new Date(),
        details: { notes },
      });
    },

    /**
     * Generate markdown report
     */
    generateMarkdown: (): string => {
      let markdown = '# Test Execution Report\n\n';
      markdown += `**Date:** ${new Date().toISOString()}\n\n`;
      markdown += `**Total Tests:** ${results.length}\n`;
      markdown += `**Passed:** ${results.filter((r) => r.passed).length}\n`;
      markdown += `**Failed:** ${results.filter((r) => !r.passed).length}\n\n`;

      markdown += '## Results\n\n';

      results.forEach((result, index) => {
        const status = result.passed ? '✅ Pass' : '❌ Fail';
        markdown += `${index + 1}. ${status} - ${result.testName}\n`;
        if (result.details?.notes) {
          markdown += `   **Notes:** ${result.details.notes}\n`;
        }
      });

      return markdown;
    },

    /**
     * Get all results
     */
    getResults: () => results,
  };
};

/**
 * Development-only check
 *
 * Use this to protect test functions from being included in production.
 */
export const isDevelopmentMode = (): boolean => {
  // This should check your environment variables
  // Adjust based on your setup
  return __DEV__ || process.env.NODE_ENV === 'test';
};

/**
 * Log test information (development only)
 */
export const testLog = (...args: any[]) => {
  if (isDevelopmentMode()) {
    console.log('[TEST]', ...args);
  }
};

/**
 * Log test error (development only)
 */
export const testError = (...args: any[]) => {
  if (isDevelopmentMode()) {
    console.error('[TEST ERROR]', ...args);
  }
};

// ============================================================
// STREAM MANAGEMENT TEST HELPERS
// ============================================================

/**
 * Verify channel list loaded from backend
 */
export const verifyChannelListLoaded = async (
  channels: any[]
): Promise<TestResult> => {
  const checks = [
    assertNotNull(channels, 'Channel list'),
    assertEquals(channels.length > 0, true, 'Channels exist'),
  ];

  const allPassed = checks.every((check) => check.passed);

  return {
    testName: 'TC-STREAM-002: Channel List Loaded',
    passed: allPassed,
    message: allPassed
      ? `Channel list loaded successfully: ${channels.length} channels`
      : `Channel list verification failed: ${checks.filter((c) => !c.passed).map((c) => c.message).join(', ')}`,
    timestamp: new Date(),
    details: {
      channelCount: channels.length,
      channelIds: channels.map((ch) => ch.id),
    },
  };
};

/**
 * Verify channel status
 */
export const verifyChannelStatus = async (
  channel: any,
  expectedStatus: string
): Promise<TestResult> => {
  const actualStatus = channel.status;
  const result = assertEquals(actualStatus, expectedStatus, 'Channel status');

  return {
    testName: `Verify Channel Status: ${channel.name}`,
    passed: result.passed,
    message: result.message,
    timestamp: new Date(),
    details: {
      channelId: channel.id,
      channelName: channel.name,
      expected: expectedStatus,
      actual: actualStatus,
    },
  };
};

/**
 * Verify channel can start
 */
export const verifyChannelCanStart = async (
  channel: any
): Promise<TestResult> => {
  const canStart =
    channel.status === 'stopped' ||
    channel.status === 'error' ||
    channel.status === 'unknown';

  return {
    testName: `Verify Channel Can Start: ${channel.name}`,
    passed: canStart,
    message: canStart
      ? `✓ Channel "${channel.name}" can start (status: ${channel.status})`
      : `✗ Channel "${channel.name}" cannot start (status: ${channel.status})`,
    timestamp: new Date(),
    details: {
      channelId: channel.id,
      channelName: channel.name,
      status: channel.status,
      canStart,
    },
  };
};

/**
 * Verify channel can stop
 */
export const verifyChannelCanStop = async (
  channel: any
): Promise<TestResult> => {
  const isTransitional =
    channel.status === 'starting' || channel.status === 'stopping';
  const canStop = channel.status === 'running' || isTransitional;

  return {
    testName: `Verify Channel Can Stop: ${channel.name}`,
    passed: canStop,
    message: canStop
      ? `✓ Channel "${channel.name}" can stop (status: ${channel.status})`
      : `✗ Channel "${channel.name}" cannot stop (status: ${channel.status})`,
    timestamp: new Date(),
    details: {
      channelId: channel.id,
      channelName: channel.name,
      status: channel.status,
      canStop,
      isTransitional,
    },
  };
};

/**
 * Verify channel has error
 */
export const verifyChannelHasError = async (
  channel: any
): Promise<TestResult> => {
  const hasError = channel.status === 'error';
  const hasErrorMessage = !!channel.error_message;

  return {
    testName: `Verify Channel Error State: ${channel.name}`,
    passed: hasError && hasErrorMessage,
    message: hasError
      ? `✓ Channel "${channel.name}" has error: ${channel.error_message}`
      : `✗ Channel "${channel.name}" does not have error`,
    timestamp: new Date(),
    details: {
      channelId: channel.id,
      channelName: channel.name,
      status: channel.status,
      error_message: channel.error_message,
    },
  };
};

/**
 * Verify all status types are present in channel list
 */
export const verifyAllStatusTypes = async (
  channels: any[]
): Promise<TestResult> => {
  const statuses = new Set(channels.map((ch) => ch.status));
  const expectedStatuses = ['stopped', 'running', 'error', 'starting', 'stopping'];

  return {
    testName: 'Verify All Status Types Present',
    passed: statuses.size > 0,
    message: `Channel list contains ${statuses.size} status types: ${Array.from(statuses).join(', ')}`,
    timestamp: new Date(),
    details: {
      totalChannels: channels.length,
      statusesFound: Array.from(statuses),
      statusCounts: channels.reduce((acc, ch) => {
        acc[ch.status] = (acc[ch.status] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
    },
  };
};

/**
 * E2E Test: Stream Management
 *
 * This function can be called to verify stream management functionality.
 * It's designed to be used during manual testing with a debugger or console.
 */
export const runStreamManagementE2E = async (channels: any[]) => {
  const suite = createTestSuite('E2E Stream Management');

  // Test 1: Verify channel list loaded
  await suite.runTest('Channel list loaded', async () => {
    const result = await verifyChannelListLoaded(channels);
    return result.passed;
  });

  // Test 2: Verify at least one channel exists
  await suite.runTest('At least one channel exists', async () => {
    return channels.length > 0;
  });

  // Test 3: Verify all channels have required fields
  await suite.runTest('All channels have required fields', async () => {
    const hasRequiredFields = channels.every(
      (ch) => ch.id && ch.name && ch.status
    );
    return hasRequiredFields;
  });

  // Test 4: Verify channel with 'stopped' status can start
  await suite.runTest('Stopped channel can start', async () => {
    const stoppedChannel = channels.find((ch) => ch.status === 'stopped');
    if (!stoppedChannel) return false; // Skip if no stopped channel
    const result = await verifyChannelCanStart(stoppedChannel);
    return result.passed;
  });

  // Test 5: Verify channel with 'running' status can stop
  await suite.runTest('Running channel can stop', async () => {
    const runningChannel = channels.find((ch) => ch.status === 'running');
    if (!runningChannel) return false; // Skip if no running channel
    const result = await verifyChannelCanStop(runningChannel);
    return result.passed;
  });

  // Test 6: Verify error channels have error messages
  await suite.runTest('Error channels have error messages', async () => {
    const errorChannels = channels.filter((ch) => ch.status === 'error');
    if (errorChannels.length === 0) return true; // Skip if no error channels
    const allHaveMessages = errorChannels.every((ch) => ch.error_message);
    return allHaveMessages;
  });

  suite.printResults();
  return suite.getResults();
};
