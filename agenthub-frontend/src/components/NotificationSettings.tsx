/**
 * Notification Settings Component
 * Allows users to control notification preferences
 */

import React, { useState, useEffect } from 'react';
import { Bell, BellOff, Volume2, VolumeX } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { notificationService } from '../services/notificationService';
import { notify } from '../services/notificationService';

export const NotificationSettings: React.FC = () => {
  const [browserNotificationsEnabled, setBrowserNotificationsEnabled] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [requestingPermission, setRequestingPermission] = useState(false);

  useEffect(() => {
    // Check current browser notification status
    setBrowserNotificationsEnabled(notificationService.isBrowserNotificationsEnabled());

    // Load sound preference from localStorage
    const savedSoundPref = localStorage.getItem('notification_sound_enabled');
    if (savedSoundPref !== null) {
      const enabled = savedSoundPref === 'true';
      setSoundEnabled(enabled);
      notificationService.setSoundEnabled(enabled);
    }
  }, []);

  const handleEnableBrowserNotifications = async () => {
    setRequestingPermission(true);
    try {
      const granted = await notificationService.requestBrowserNotificationPermission();
      setBrowserNotificationsEnabled(granted);

      if (granted) {
        notify.success('Browser notifications enabled!');
      } else {
        notify.warning('Browser notifications permission denied');
      }
    } catch (error) {
      notify.error('Failed to enable browser notifications');
    } finally {
      setRequestingPermission(false);
    }
  };

  const handleToggleSound = () => {
    const newValue = !soundEnabled;
    setSoundEnabled(newValue);
    notificationService.setSoundEnabled(newValue);
    localStorage.setItem('notification_sound_enabled', String(newValue));

    if (newValue) {
      notify.info('Notification sounds enabled');
    } else {
      notify.info('Notification sounds disabled');
    }
  };

  const testNotifications = () => {
    // Test different notification types
    notify.info('This is an info notification');
    setTimeout(() => notify.success('This is a success notification'), 1000);
    setTimeout(() => notify.warning('This is a warning notification'), 2000);
    setTimeout(() => notify.error('This is an error notification'), 3000);

    if (browserNotificationsEnabled) {
      setTimeout(() => {
        notify.entityChange('branch', 'deleted', 'test-branch', 'test-id', 'Test User');
      }, 4000);
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Notification Settings
        </CardTitle>
        <CardDescription>
          Control how you receive notifications about data changes
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Browser Notifications */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              {browserNotificationsEnabled ? (
                <Bell className="h-4 w-4 text-green-500" />
              ) : (
                <BellOff className="h-4 w-4 text-gray-400" />
              )}
              <span className="font-medium">Browser Notifications</span>
            </div>
            <p className="text-sm text-gray-500">
              Get desktop notifications for important events
            </p>
          </div>
          {!browserNotificationsEnabled ? (
            <Button
              size="sm"
              onClick={handleEnableBrowserNotifications}
              disabled={requestingPermission}
            >
              {requestingPermission ? 'Requesting...' : 'Enable'}
            </Button>
          ) : (
            <span className="text-sm text-green-500">Enabled</span>
          )}
        </div>

        {/* Sound Notifications */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              {soundEnabled ? (
                <Volume2 className="h-4 w-4 text-green-500" />
              ) : (
                <VolumeX className="h-4 w-4 text-gray-400" />
              )}
              <span className="font-medium">Notification Sounds</span>
            </div>
            <p className="text-sm text-gray-500">
              Play a sound when notifications appear
            </p>
          </div>
          <Button
            size="sm"
            variant={soundEnabled ? 'destructive' : 'default'}
            onClick={handleToggleSound}
          >
            {soundEnabled ? 'Disable' : 'Enable'}
          </Button>
        </div>

        {/* Test Notifications */}
        <div className="pt-4 border-t">
          <Button
            className="w-full"
            variant="outline"
            onClick={testNotifications}
          >
            Test Notifications
          </Button>
        </div>

        {/* Notification Types Info */}
        <div className="pt-4 border-t space-y-2">
          <p className="text-sm font-medium">Notification Types:</p>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• <span className="font-medium">Toast:</span> In-app notifications for all events</li>
            <li>• <span className="font-medium">Desktop:</span> Branch/Project deletions, Task completions</li>
            <li>• <span className="font-medium">Sound:</span> Success, Warning, and Error events</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};