/**
 * Jest setup file for JavaScript SDK tests
 */

// Mock cross-fetch globally
global.fetch = jest.fn();

// Clean up mocks after each test
afterEach(() => {
  jest.clearAllMocks();
});
