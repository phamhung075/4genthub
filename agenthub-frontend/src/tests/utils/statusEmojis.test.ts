/**
 * @fileoverview Test suite for statusEmojis utility
 * Tests status to emoji mapping functionality
 */

import { getStatusEmoji, getStatusLabel, getStatusColor, isValidStatus } from '../../utils/statusEmojis';

describe('statusEmojis', () => {
  describe('getStatusEmoji', () => {
    it('should return correct emoji for each status', () => {
      expect(getStatusEmoji('todo')).toBe('📋');
      expect(getStatusEmoji('in_progress')).toBe('⏳');
      expect(getStatusEmoji('done')).toBe('✅');
      expect(getStatusEmoji('cancelled')).toBe('❌');
      expect(getStatusEmoji('blocked')).toBe('🚫');
      expect(getStatusEmoji('review')).toBe('👀');
      expect(getStatusEmoji('testing')).toBe('🧪');
    });

    it('should return default emoji for unknown status', () => {
      expect(getStatusEmoji('unknown')).toBe('❓');
      expect(getStatusEmoji('')).toBe('❓');
      expect(getStatusEmoji(null as any)).toBe('❓');
      expect(getStatusEmoji(undefined as any)).toBe('❓');
    });

    it('should be case insensitive', () => {
      expect(getStatusEmoji('TODO')).toBe('📋');
      expect(getStatusEmoji('In_Progress')).toBe('⏳');
      expect(getStatusEmoji('DONE')).toBe('✅');
    });

    it('should handle status with extra spaces', () => {
      expect(getStatusEmoji('  todo  ')).toBe('📋');
      expect(getStatusEmoji(' in_progress ')).toBe('⏳');
    });
  });

  describe('getStatusLabel', () => {
    it('should return human-readable labels', () => {
      expect(getStatusLabel('todo')).toBe('To Do');
      expect(getStatusLabel('in_progress')).toBe('In Progress');
      expect(getStatusLabel('done')).toBe('Done');
      expect(getStatusLabel('cancelled')).toBe('Cancelled');
      expect(getStatusLabel('blocked')).toBe('Blocked');
      expect(getStatusLabel('review')).toBe('Review');
      expect(getStatusLabel('testing')).toBe('Testing');
    });

    it('should return status as-is for unknown status', () => {
      expect(getStatusLabel('unknown')).toBe('Unknown');
      expect(getStatusLabel('custom_status')).toBe('Custom Status');
    });

    it('should handle empty/null status', () => {
      expect(getStatusLabel('')).toBe('Unknown');
      expect(getStatusLabel(null as any)).toBe('Unknown');
      expect(getStatusLabel(undefined as any)).toBe('Unknown');
    });

    it('should capitalize properly', () => {
      expect(getStatusLabel('some_weird_status')).toBe('Some Weird Status');
      expect(getStatusLabel('ALL_CAPS_STATUS')).toBe('All Caps Status');
    });
  });

  describe('getStatusColor', () => {
    it('should return correct color classes for each status', () => {
      expect(getStatusColor('todo')).toBe('text-gray-600');
      expect(getStatusColor('in_progress')).toBe('text-blue-600');
      expect(getStatusColor('done')).toBe('text-green-600');
      expect(getStatusColor('cancelled')).toBe('text-red-600');
      expect(getStatusColor('blocked')).toBe('text-orange-600');
      expect(getStatusColor('review')).toBe('text-purple-600');
      expect(getStatusColor('testing')).toBe('text-yellow-600');
    });

    it('should return default color for unknown status', () => {
      expect(getStatusColor('unknown')).toBe('text-gray-500');
      expect(getStatusColor('')).toBe('text-gray-500');
    });

    it('should handle background colors', () => {
      expect(getStatusColor('todo', 'bg')).toBe('bg-gray-600');
      expect(getStatusColor('in_progress', 'bg')).toBe('bg-blue-600');
      expect(getStatusColor('done', 'bg')).toBe('bg-green-600');
    });

    it('should handle border colors', () => {
      expect(getStatusColor('todo', 'border')).toBe('border-gray-600');
      expect(getStatusColor('in_progress', 'border')).toBe('border-blue-600');
    });

    it('should handle ring colors', () => {
      expect(getStatusColor('todo', 'ring')).toBe('ring-gray-600');
      expect(getStatusColor('blocked', 'ring')).toBe('ring-orange-600');
    });

    it('should default to text prefix for invalid type', () => {
      expect(getStatusColor('todo', 'invalid' as any)).toBe('text-gray-600');
    });
  });

  describe('isValidStatus', () => {
    it('should validate known statuses', () => {
      expect(isValidStatus('todo')).toBe(true);
      expect(isValidStatus('in_progress')).toBe(true);
      expect(isValidStatus('done')).toBe(true);
      expect(isValidStatus('cancelled')).toBe(true);
      expect(isValidStatus('blocked')).toBe(true);
      expect(isValidStatus('review')).toBe(true);
      expect(isValidStatus('testing')).toBe(true);
    });

    it('should reject invalid statuses', () => {
      expect(isValidStatus('unknown')).toBe(false);
      expect(isValidStatus('random')).toBe(false);
      expect(isValidStatus('')).toBe(false);
      expect(isValidStatus(null as any)).toBe(false);
      expect(isValidStatus(undefined as any)).toBe(false);
      expect(isValidStatus(123 as any)).toBe(false);
    });

    it('should be case insensitive', () => {
      expect(isValidStatus('TODO')).toBe(true);
      expect(isValidStatus('In_Progress')).toBe(true);
      expect(isValidStatus('DONE')).toBe(true);
    });

    it('should handle trimmed values', () => {
      expect(isValidStatus('  todo  ')).toBe(true);
      expect(isValidStatus(' blocked ')).toBe(true);
    });
  });

  describe('Status emoji with label', () => {
    it('should combine emoji and label nicely', () => {
      const statuses = ['todo', 'in_progress', 'done', 'blocked'];
      
      statuses.forEach(status => {
        const emoji = getStatusEmoji(status);
        const label = getStatusLabel(status);
        const combined = `${emoji} ${label}`;
        
        expect(combined).toMatch(/^[^\s]+ .+$/); // emoji followed by space and text
      });
    });
  });

  describe('Edge cases', () => {
    it('should handle numeric input gracefully', () => {
      expect(getStatusEmoji(123 as any)).toBe('❓');
      expect(getStatusLabel(456 as any)).toBe('Unknown');
      expect(getStatusColor(789 as any)).toBe('text-gray-500');
    });

    it('should handle object input gracefully', () => {
      expect(getStatusEmoji({} as any)).toBe('❓');
      expect(getStatusLabel({} as any)).toBe('Unknown');
      expect(getStatusColor({} as any)).toBe('text-gray-500');
    });

    it('should handle array input gracefully', () => {
      expect(getStatusEmoji([] as any)).toBe('❓');
      expect(getStatusLabel([] as any)).toBe('Unknown');
      expect(getStatusColor([] as any)).toBe('text-gray-500');
    });
  });

  describe('Consistency checks', () => {
    const validStatuses = ['todo', 'in_progress', 'done', 'cancelled', 'blocked', 'review', 'testing'];

    it('should have emoji for all valid statuses', () => {
      validStatuses.forEach(status => {
        const emoji = getStatusEmoji(status);
        expect(emoji).not.toBe('❓');
        expect(emoji).toBeTruthy();
      });
    });

    it('should have label for all valid statuses', () => {
      validStatuses.forEach(status => {
        const label = getStatusLabel(status);
        expect(label).not.toBe('Unknown');
        expect(label).toBeTruthy();
      });
    });

    it('should have color for all valid statuses', () => {
      validStatuses.forEach(status => {
        const color = getStatusColor(status);
        expect(color).not.toBe('text-gray-500');
        expect(color).toMatch(/^text-\w+-600$/);
      });
    });
  });
});