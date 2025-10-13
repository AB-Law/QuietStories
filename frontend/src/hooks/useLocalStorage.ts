/**
 * Custom hook for localStorage management with TypeScript support.
 *
 * This hook provides a React-friendly interface for localStorage operations
 * with proper error handling and JSON serialization/deserialization.
 */

import { useState, useEffect, useCallback } from 'react';

type SetValue<T> = (value: T | ((val: T) => T)) => void;

/**
 * Custom hook for localStorage with React state synchronization.
 *
 * @param key - localStorage key
 * @param initialValue - Initial value if no stored value exists
 * @returns Tuple of [storedValue, setValue] similar to useState
 *
 * @example
 * ```typescript
 * const [playerName, setPlayerName] = useLocalStorage('playerName', '');
 * ```
 */
export function useLocalStorage<T>(key: string, initialValue: T): [T, SetValue<T>] {
  // State to store our value
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      // Get from local storage by key
      const item = window.localStorage.getItem(key);
      // Parse stored json or if none return initialValue
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      // If error parsing JSON, return initialValue
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Return a wrapped version of useState's setter function that ...
  // ... persists the new value to localStorage.
  const setValue: SetValue<T> = useCallback((value) => {
    try {
      // Allow value to be a function so we have the same API as useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;

      // Save state
      setStoredValue(valueToStore);

      // Save to local storage
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      // A more advanced implementation would handle the error case
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  // Listen for changes in localStorage from other tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue));
        } catch (error) {
          console.warn(`Error parsing storage event for key "${key}":`, error);
        }
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('storage', handleStorageChange);
      return () => window.removeEventListener('storage', handleStorageChange);
    }
  }, [key]);

  return [storedValue, setValue];
}

/**
 * Hook for managing user settings in localStorage.
 *
 * @returns Object with settings state and update functions
 */
export function useUserSettings() {
  const [settings, setSettings] = useLocalStorage('quietstories-user-settings', {
    playerName: '',
    preferences: {}
  });

  const updatePlayerName = useCallback((playerName: string) => {
    setSettings(prev => ({ ...prev, playerName }));
  }, [setSettings]);

  const updatePreferences = useCallback((preferences: Record<string, any>) => {
    setSettings(prev => ({ ...prev, preferences }));
  }, [setSettings]);

  const clearSettings = useCallback(() => {
    setSettings({ playerName: '', preferences: {} });
  }, [setSettings]);

  return {
    settings,
    updatePlayerName,
    updatePreferences,
    clearSettings,
    setSettings
  };
}
