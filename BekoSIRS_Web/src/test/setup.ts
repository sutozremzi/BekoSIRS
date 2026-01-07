// src/test/setup.ts
// Global test setup for Vitest + React Testing Library

import '@testing-library/jest-dom';

// Mock localStorage with actual storage
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
    getItem: (key: string) => localStorageStore[key] || null,
    setItem: (key: string, value: string) => { localStorageStore[key] = value; },
    removeItem: (key: string) => { delete localStorageStore[key]; },
    clear: () => { Object.keys(localStorageStore).forEach(key => delete localStorageStore[key]); },
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Mock fetch for API calls
global.fetch = vi.fn();

// Reset mocks before each test
beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
});
