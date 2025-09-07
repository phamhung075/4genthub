import { getBranchContext, getTaskContext } from '../api';

// Mock fetch
global.fetch = jest.fn();

describe('Context API Functions', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  describe('getBranchContext', () => {
    it('should call manage_context with correct branch level', async () => {
      // Arrange
      const branchId = 'd4f91ee3-1f97-4768-b4ff-1e734180f874';
      const mockResponse = {
        success: true,
        context: {
          id: branchId,
          level: 'branch',
          data: { branch_name: 'feature/auth-system' }
        }
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: {
            content: [{
              text: JSON.stringify(mockResponse)
            }]
          }
        })
      });

      // Act
      const result = await getBranchContext(branchId);

      // Assert
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/mcp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('"name":"manage_context"')
      });

      // Verify the request body contains correct parameters
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const requestBody = JSON.parse(callArgs[1].body);
      
      expect(requestBody.params.arguments).toEqual({
        action: 'resolve',
        level: 'branch',
        context_id: branchId,
        force_refresh: false,
        include_inherited: true
      });

      expect(result).toEqual(mockResponse);
    });

    it('should handle branch context not found error', async () => {
      // Arrange
      const branchId = 'non-existent-branch-id';
      const errorResponse = {
        success: false,
        error: 'Context not found: non-existent-branch-id'
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: {
            content: [{
              text: JSON.stringify(errorResponse)
            }]
          }
        })
      });

      // Act
      const result = await getBranchContext(branchId);

      // Assert
      expect(result).toEqual(errorResponse);
      expect(result.success).toBe(false);
      expect(result.error).toContain('Context not found');
    });
  });

  describe('getTaskContext', () => {
    it('should call manage_context with correct task level', async () => {
      // Arrange
      const taskId = 'a5f91ee3-2b97-4768-c5ff-2e834290f985';
      const mockResponse = {
        success: true,
        context: {
          id: taskId,
          level: 'task',
          data: { task_title: 'Implement login' }
        }
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: {
            content: [{
              text: JSON.stringify(mockResponse)
            }]
          }
        })
      });

      // Act
      const result = await getTaskContext(taskId);

      // Assert
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/mcp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('"name":"manage_context"')
      });

      // Verify the request body contains correct parameters
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const requestBody = JSON.parse(callArgs[1].body);
      
      expect(requestBody.params.arguments).toEqual({
        action: 'resolve',
        level: 'task',
        context_id: taskId,
        force_refresh: false,
        include_inherited: true
      });

      expect(result).toEqual(mockResponse);
    });

    it('should handle task context not found error', async () => {
      // Arrange
      const taskId = 'non-existent-task-id';
      const errorResponse = {
        success: false,
        error: 'Context not found: non-existent-task-id'
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: {
            content: [{
              text: JSON.stringify(errorResponse)
            }]
          }
        })
      });

      // Act
      const result = await getTaskContext(taskId);

      // Assert
      expect(result).toEqual(errorResponse);
      expect(result.success).toBe(false);
      expect(result.error).toContain('Context not found');
    });
  });

  describe('Context Level Differentiation', () => {
    it('should not use task level for branch IDs', async () => {
      // This test ensures we don't accidentally use getTaskContext for branch IDs
      const branchId = 'd4f91ee3-1f97-4768-b4ff-1e734180f874';
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ result: { success: true } })
      });

      // Act - Call getBranchContext (not getTaskContext)
      await getBranchContext(branchId);

      // Assert - Verify it's using branch level
      const requestBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
      expect(requestBody.params.arguments.level).toBe('branch');
      expect(requestBody.params.arguments.action).toBe('resolve');
    });

    it('should handle inheritance data correctly for branches', async () => {
      // Arrange
      const branchId = 'd4f91ee3-1f97-4768-b4ff-1e734180f874';
      const mockResponse = {
        success: true,
        context: {
          id: branchId,
          level: 'branch',
          data: { branch_name: 'feature/auth-system' }
        },
        inherited_context: {
          project: { id: 'proj-123', data: { name: 'Test Project' } },
          global: { id: 'global_singleton', data: { org: 'DhafnckMCP' } }
        }
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ 
          result: {
            content: [{
              text: JSON.stringify(mockResponse)
            }]
          }
        })
      });

      // Act
      const result = await getBranchContext(branchId);

      // Assert
      expect(result.inherited_context).toBeDefined();
      expect(result.inherited_context.project).toBeDefined();
      expect(result.inherited_context.global).toBeDefined();
      // Branch context should not inherit from itself
      expect(result.inherited_context.branch).toBeUndefined();
    });

    it('should handle inheritance data correctly for tasks', async () => {
      // Arrange
      const taskId = 'task-123';
      const mockResponse = {
        success: true,
        context: {
          id: taskId,
          level: 'task',
          data: { task_title: 'Test Task' }
        },
        inherited_context: {
          branch: { id: 'branch-123', data: { branch_name: 'feature' } },
          project: { id: 'proj-123', data: { name: 'Test Project' } },
          global: { id: 'global_singleton', data: { org: 'DhafnckMCP' } }
        }
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ 
          result: {
            content: [{
              text: JSON.stringify(mockResponse)
            }]
          }
        })
      });

      // Act
      const result = await getTaskContext(taskId);

      // Assert
      expect(result.inherited_context).toBeDefined();
      expect(result.inherited_context.branch).toBeDefined();
      expect(result.inherited_context.project).toBeDefined();
      expect(result.inherited_context.global).toBeDefined();
    });
  });
});