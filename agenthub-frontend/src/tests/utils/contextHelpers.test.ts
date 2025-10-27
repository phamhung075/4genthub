/**
 * @fileoverview Test suite for contextHelpers utility functions
 * Tests context data manipulation and helper functions
 */

import {
  parseContextData,
  stringifyContextData,
  mergeContextData,
  extractContextValue,
  isValidContextData,
  sanitizeContextData
} from '../../utils/contextHelpers';

describe('contextHelpers', () => {
  describe('parseContextData', () => {
    it('should parse valid JSON string', () => {
      const jsonString = '{"key": "value", "number": 123}';
      const result = parseContextData(jsonString);
      
      expect(result).toEqual({
        key: 'value',
        number: 123
      });
    });

    it('should return empty object for invalid JSON', () => {
      const invalidJson = 'not valid json';
      const result = parseContextData(invalidJson);
      
      expect(result).toEqual({});
    });

    it('should return empty object for empty string', () => {
      const result = parseContextData('');
      
      expect(result).toEqual({});
    });

    it('should return empty object for null/undefined', () => {
      expect(parseContextData(null as any)).toEqual({});
      expect(parseContextData(undefined as any)).toEqual({});
    });

    it('should handle nested objects', () => {
      const nested = '{"level1": {"level2": {"level3": "value"}}}';
      const result = parseContextData(nested);
      
      expect(result).toEqual({
        level1: {
          level2: {
            level3: 'value'
          }
        }
      });
    });

    it('should handle arrays in JSON', () => {
      const withArray = '{"items": [1, 2, 3], "tags": ["a", "b"]}';
      const result = parseContextData(withArray);
      
      expect(result).toEqual({
        items: [1, 2, 3],
        tags: ['a', 'b']
      });
    });
  });

  describe('stringifyContextData', () => {
    it('should stringify object to JSON', () => {
      const obj = { key: 'value', number: 123 };
      const result = stringifyContextData(obj);
      
      expect(result).toBe('{"key":"value","number":123}');
    });

    it('should return empty string for null/undefined', () => {
      expect(stringifyContextData(null)).toBe('');
      expect(stringifyContextData(undefined)).toBe('');
    });

    it('should handle empty object', () => {
      const result = stringifyContextData({});
      
      expect(result).toBe('{}');
    });

    it('should handle nested objects', () => {
      const nested = {
        level1: {
          level2: {
            level3: 'value'
          }
        }
      };
      const result = stringifyContextData(nested);
      
      expect(JSON.parse(result)).toEqual(nested);
    });

    it('should handle circular references gracefully', () => {
      const obj: any = { a: 1 };
      obj.circular = obj; // Create circular reference
      
      // Should not throw error
      expect(() => stringifyContextData(obj)).not.toThrow();
    });
  });

  describe('mergeContextData', () => {
    it('should merge two context objects', () => {
      const base = { a: 1, b: 2 };
      const update = { b: 3, c: 4 };
      
      const result = mergeContextData(base, update);
      
      expect(result).toEqual({
        a: 1,
        b: 3, // Updated
        c: 4  // Added
      });
    });

    it('should handle null/undefined base', () => {
      const update = { a: 1 };
      
      expect(mergeContextData(null, update)).toEqual(update);
      expect(mergeContextData(undefined, update)).toEqual(update);
    });

    it('should handle null/undefined update', () => {
      const base = { a: 1 };
      
      expect(mergeContextData(base, null)).toEqual(base);
      expect(mergeContextData(base, undefined)).toEqual(base);
    });

    it('should deep merge nested objects', () => {
      const base = {
        user: {
          name: 'John',
          settings: {
            theme: 'dark'
          }
        }
      };
      
      const update = {
        user: {
          settings: {
            language: 'en'
          }
        }
      };
      
      const result = mergeContextData(base, update);
      
      expect(result).toEqual({
        user: {
          name: 'John',
          settings: {
            theme: 'dark',
            language: 'en'
          }
        }
      });
    });

    it('should handle arrays correctly', () => {
      const base = { tags: ['a', 'b'] };
      const update = { tags: ['c', 'd'] };
      
      const result = mergeContextData(base, update);
      
      // Arrays should be replaced, not merged
      expect(result).toEqual({
        tags: ['c', 'd']
      });
    });
  });

  describe('extractContextValue', () => {
    it('should extract value by path', () => {
      const context = {
        user: {
          profile: {
            name: 'John Doe'
          }
        }
      };
      
      const result = extractContextValue(context, 'user.profile.name');
      
      expect(result).toBe('John Doe');
    });

    it('should return undefined for non-existent path', () => {
      const context = { a: 1 };
      
      const result = extractContextValue(context, 'b.c.d');
      
      expect(result).toBeUndefined();
    });

    it('should handle array indices', () => {
      const context = {
        items: [
          { id: 1 },
          { id: 2 },
          { id: 3 }
        ]
      };
      
      const result = extractContextValue(context, 'items.1.id');
      
      expect(result).toBe(2);
    });

    it('should return default value if path not found', () => {
      const context = { a: 1 };
      
      const result = extractContextValue(context, 'b.c', 'default');
      
      expect(result).toBe('default');
    });

    it('should handle empty path', () => {
      const context = { a: 1 };
      
      const result = extractContextValue(context, '');
      
      expect(result).toEqual(context);
    });
  });

  describe('isValidContextData', () => {
    it('should validate proper context object', () => {
      const valid = {
        key: 'value',
        nested: {
          data: true
        }
      };
      
      expect(isValidContextData(valid)).toBe(true);
    });

    it('should reject non-objects', () => {
      expect(isValidContextData('string')).toBe(false);
      expect(isValidContextData(123)).toBe(false);
      expect(isValidContextData(true)).toBe(false);
      expect(isValidContextData([])).toBe(false);
    });

    it('should reject null/undefined', () => {
      expect(isValidContextData(null)).toBe(false);
      expect(isValidContextData(undefined)).toBe(false);
    });

    it('should accept empty object', () => {
      expect(isValidContextData({})).toBe(true);
    });

    it('should validate nested structures', () => {
      const complex = {
        level1: {
          level2: {
            arrays: [1, 2, 3],
            objects: { a: 1 }
          }
        }
      };
      
      expect(isValidContextData(complex)).toBe(true);
    });
  });

  describe('sanitizeContextData', () => {
    it('should remove null and undefined values', () => {
      const dirty = {
        a: 1,
        b: null,
        c: undefined,
        d: 'value'
      };
      
      const result = sanitizeContextData(dirty);
      
      expect(result).toEqual({
        a: 1,
        d: 'value'
      });
    });

    it('should handle nested sanitization', () => {
      const nested = {
        user: {
          name: 'John',
          age: null,
          profile: {
            bio: 'Hello',
            avatar: undefined
          }
        }
      };
      
      const result = sanitizeContextData(nested);
      
      expect(result).toEqual({
        user: {
          name: 'John',
          profile: {
            bio: 'Hello'
          }
        }
      });
    });

    it('should remove empty strings if specified', () => {
      const withEmpty = {
        a: '',
        b: 'value',
        c: '   '
      };
      
      const result = sanitizeContextData(withEmpty, { removeEmpty: true });
      
      expect(result).toEqual({
        b: 'value'
      });
    });

    it('should preserve falsy values except null/undefined', () => {
      const falsy = {
        zero: 0,
        false: false,
        empty: '',
        null: null,
        undefined: undefined
      };
      
      const result = sanitizeContextData(falsy);
      
      expect(result).toEqual({
        zero: 0,
        false: false,
        empty: ''
      });
    });

    it('should handle arrays in objects', () => {
      const withArrays = {
        tags: ['a', null, 'b', undefined, 'c'],
        values: [1, 2, null, 3]
      };
      
      const result = sanitizeContextData(withArrays);
      
      expect(result).toEqual({
        tags: ['a', 'b', 'c'],
        values: [1, 2, 3]
      });
    });
  });

  describe('Integration scenarios', () => {
    it('should handle parse -> merge -> stringify workflow', () => {
      const json1 = '{"a": 1, "b": {"c": 2}}';
      const json2 = '{"b": {"d": 3}, "e": 4}';
      
      const obj1 = parseContextData(json1);
      const obj2 = parseContextData(json2);
      const merged = mergeContextData(obj1, obj2);
      const result = stringifyContextData(merged);
      
      expect(JSON.parse(result)).toEqual({
        a: 1,
        b: {
          c: 2,
          d: 3
        },
        e: 4
      });
    });

    it('should handle sanitize -> validate workflow', () => {
      const dirty = {
        valid: 'data',
        invalid: null,
        nested: {
          good: 'value',
          bad: undefined
        }
      };
      
      const cleaned = sanitizeContextData(dirty);
      
      expect(isValidContextData(cleaned)).toBe(true);
      expect(cleaned).toEqual({
        valid: 'data',
        nested: {
          good: 'value'
        }
      });
    });
  });
});