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
