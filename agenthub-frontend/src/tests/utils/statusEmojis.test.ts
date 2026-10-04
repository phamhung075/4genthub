import { describe, expect, it } from 'vitest';
import { getEntityEmoji, getPriorityEmoji, getStatusEmoji } from '../../utils/statusEmojis';

describe('statusEmojis', () => {
  describe('getStatusEmoji', () => {
    it.each([
      ['todo', '📋'],
      ['in_progress', '⚙️'],
      ['blocked', '🚫'],
      ['review', '👀'],
      ['testing', '🧪'],
      ['done', '✅'],
      ['completed', '✅'],
      ['cancelled', '❌'],
    ])('maps %s to its emoji', (status, emoji) => {
      expect(getStatusEmoji(status)).toBe(emoji);
    });

    it('is case insensitive', () => {
      expect(getStatusEmoji('TODO')).toBe('📋');
      expect(getStatusEmoji('In_Progress')).toBe('⚙️');
    });

    it('returns the question mark for an unknown or empty status', () => {
      expect(getStatusEmoji('unknown')).toBe('❓');
      expect(getStatusEmoji('')).toBe('❓');
    });
  });

  describe('getPriorityEmoji', () => {
    it.each([
      ['critical', '🔴'],
      ['high', '🔴'],
      ['urgent', '🔴'],
      ['medium', '🟡'],
      ['low', '🟢'],
    ])('maps %s to its emoji', (priority, emoji) => {
      expect(getPriorityEmoji(priority)).toBe(emoji);
    });

    it('is case insensitive and falls back to the white circle', () => {
      expect(getPriorityEmoji('HIGH')).toBe('🔴');
      expect(getPriorityEmoji('whenever')).toBe('⚪');
    });
  });

  describe('getEntityEmoji', () => {
    it('reads the status or the priority of the entity by the requested type', () => {
      const entity = { status: 'done', priority: 'low' };
      expect(getEntityEmoji(entity, 'status')).toBe('✅');
      expect(getEntityEmoji(entity, 'priority')).toBe('🟢');
    });

    it('returns the white circle when the requested field is missing', () => {
      expect(getEntityEmoji({ priority: 'low' }, 'status')).toBe('⚪');
      expect(getEntityEmoji({ status: 'done' }, 'priority')).toBe('⚪');
    });
  });
});
