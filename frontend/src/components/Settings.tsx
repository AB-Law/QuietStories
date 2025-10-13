/**
 * Settings management component for user preferences
 */

import { useState, useEffect } from 'react';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { apiService } from '../services/api';
import type { UserSettings, SettingsRequest } from '../services/api';
import { useUserSettings } from '../hooks/useLocalStorage';
import { Save, User, AlertCircle } from 'lucide-react';

interface SettingsProps {
  onSettingsChange?: (settings: { playerName: string; preferences: Record<string, any> }) => void;
}

export function Settings({ onSettingsChange }: SettingsProps) {
  const { settings: localSettings, updatePlayerName } = useUserSettings();
  const [playerName, setPlayerName] = useState(localSettings.playerName || '');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [serverSettings, setServerSettings] = useState<UserSettings | null>(null);

  // Load settings from server on component mount
  useEffect(() => {
    loadServerSettings();
  }, []);

  // Sync with localStorage
  useEffect(() => {
    setPlayerName(localSettings.playerName || '');
  }, [localSettings.playerName]);

  const loadServerSettings = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const settings = await apiService.getUserSettings();
      setServerSettings(settings);

      // Sync with local storage if server has more recent data
      if (settings.player_name && settings.player_name !== localSettings.playerName) {
        updatePlayerName(settings.player_name);
        setPlayerName(settings.player_name);
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('Settings not found')) {
        // No settings on server yet, that's okay
        setServerSettings(null);
      } else {
        console.warn('Failed to load server settings:', error);
        setError('Failed to load settings from server. Using local settings.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!playerName.trim()) {
      setError('Player name is required');
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const request: SettingsRequest = {
        player_name: playerName.trim(),
        preferences: localSettings.preferences || {}
      };

      let result: UserSettings;

      if (serverSettings) {
        // Update existing settings
        result = await apiService.updateUserSettings(request);
      } else {
        // Create new settings
        result = await apiService.saveUserSettings(request);
      }

      // Update local storage
      updatePlayerName(result.player_name);
      setServerSettings(result);
      setSuccess(true);

      // Notify parent component of changes
      if (onSettingsChange) {
        onSettingsChange({
          playerName: result.player_name,
          preferences: result.preferences
        });
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setError(error instanceof Error ? error.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePlayerNameChange = (value: string) => {
    setPlayerName(value);
    setError(null);
    setSuccess(false);

    // Update localStorage immediately for responsive UI
    updatePlayerName(value);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
        <span className="ml-2 text-sm text-muted-foreground">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <User className="h-4 w-4" />
        <h3 className="text-sm font-medium">Player Settings</h3>
      </div>

      <div className="space-y-3">
        <div>
          <label htmlFor="player-name" className="text-sm font-medium block mb-2">
            Player Name
          </label>
          <Input
            id="player-name"
            type="text"
            placeholder="Enter your preferred name"
            value={playerName}
            onChange={(e) => handlePlayerNameChange(e.target.value)}
            className="w-full"
            maxLength={100}
          />
          <p className="text-xs text-muted-foreground mt-1">
            This name will be used for your character in new games
          </p>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {error && (
              <div className="flex items-center gap-1 text-red-600">
                <AlertCircle className="h-3 w-3" />
                <span className="text-xs">{error}</span>
              </div>
            )}
            {success && (
              <span className="text-xs text-green-600">Settings saved successfully!</span>
            )}
          </div>

          <Button
            onClick={saveSettings}
            disabled={isSaving || !playerName.trim()}
            size="sm"
            className="gap-2"
          >
            {isSaving ? (
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
            ) : (
              <Save className="h-3 w-3" />
            )}
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>

        <div className="text-xs text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>Local storage:</span>
            <span className={localSettings.playerName ? 'text-green-600' : 'text-gray-500'}>
              {localSettings.playerName || 'Not set'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Server storage:</span>
            <span className={serverSettings?.player_name ? 'text-green-600' : 'text-gray-500'}>
              {serverSettings?.player_name || 'Not set'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
