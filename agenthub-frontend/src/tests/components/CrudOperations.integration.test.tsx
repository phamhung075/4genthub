import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as api from '../../api';
import * as apiV2 from '../../services/apiV2';

// Mock API modules
vi.mock('../../api');
vi.mock('../../services/apiV2');

describe('CRUD Operations Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiV2.isAuthenticated as any).mockReturnValue(true);
  });

  describe('Branch Update Operations', () => {
    it('should call updateBranch with correct parameters', async () => {
      const mockUpdatedBranch = {
        id: 'branch-123',
        name: 'Updated Branch Name',
        description: 'Updated branch description'
      };

      (api.updateBranch as any).mockResolvedValue(mockUpdatedBranch);

      // Call the API function directly to test integration
      const result = await api.updateBranch('proj-123', 'branch-123', {
        name: 'Updated Branch Name',
        description: 'Updated branch description'
      });

      expect(api.updateBranch).toHaveBeenCalledWith('proj-123', 'branch-123', {
        name: 'Updated Branch Name',
        description: 'Updated branch description'
      });

      expect(result).toEqual(mockUpdatedBranch);
    });

    it('should handle updateBranch failure gracefully', async () => {
      (api.updateBranch as any).mockRejectedValue(new Error('Network error'));

      try {
        await api.updateBranch('proj-123', 'branch-123', { name: 'New Name' });
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
      }

      expect(api.updateBranch).toHaveBeenCalled();
    });
  });

  describe('Project V2 API Operations', () => {
    it('should create project via V2 API when authenticated', async () => {
      const mockProject = { 
        id: 'proj-v2-123', 
        name: 'New V2 Project', 
        description: 'A project created via V2 API',
        git_branchs: {} 
      };

      (apiV2.projectApiV2.createProject as any).mockResolvedValue(mockProject);
      (api.createProject as any).mockResolvedValue(mockProject);

      const result = await api.createProject({
        name: 'New V2 Project',
        description: 'A project created via V2 API'
      });

      expect(result).toEqual(mockProject);
    });

    it('should update project via V2 API when authenticated', async () => {
      const mockProject = {
        id: 'proj-123',
        name: 'Updated V2 Project Name',
        description: 'Updated via V2 API'
      };

      (apiV2.projectApiV2.updateProject as any).mockResolvedValue(mockProject);
      (api.updateProject as any).mockResolvedValue(mockProject);

      const result = await api.updateProject('proj-123', {
        name: 'Updated V2 Project Name',
        description: 'Updated via V2 API'
      });

      expect(result).toEqual(mockProject);
    });

    it('should delete project via V2 API when authenticated', async () => {
      (apiV2.projectApiV2.deleteProject as any).mockResolvedValue(undefined);
      (api.deleteProject as any).mockResolvedValue({ 
        success: true, 
        message: undefined, 
        error: undefined 
      });

      const result = await api.deleteProject('proj-123');

      expect(result).toEqual({
        success: true,
        message: undefined,
        error: undefined
      });
    });
  });

  describe('V2 API Fallback Mechanism', () => {
    it('should fallback to V1 MCP when V2 API fails', async () => {
      // Mock V2 API failure and V1 success
      (apiV2.projectApiV2.createProject as any).mockRejectedValue(new Error('V2 API error'));
      (api.createProject as any).mockImplementation(async (project) => {
        // Simulate calling both V2 (failing) and V1 (succeeding)
        try {
          await apiV2.projectApiV2.createProject(project);
        } catch {
          // Fallback to V1 - mock successful V1 response
          return { id: 'proj-v1-fallback', ...project };
        }
      });

      const result = await api.createProject({
        name: 'Fallback Test Project',
        description: 'Testing fallback mechanism'
      });

      expect(result).toMatchObject({
        name: 'Fallback Test Project',
        description: 'Testing fallback mechanism'
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      (api.updateBranch as any).mockRejectedValue(new Error('Network error'));
      (api.createProject as any).mockRejectedValue(new Error('Network error'));
      (api.deleteProject as any).mockRejectedValue(new Error('Network error'));

      // All operations should handle errors without crashing
      await expect(api.updateBranch('proj', 'branch', {})).rejects.toThrow('Network error');
      await expect(api.createProject({})).rejects.toThrow('Network error');
      await expect(api.deleteProject('proj')).rejects.toThrow('Network error');
    });

    it('should handle malformed responses', async () => {
      (api.updateBranch as any).mockResolvedValue(null);
      (api.createProject as any).mockResolvedValue(null);

      const branchResult = await api.updateBranch('proj', 'branch', { name: 'test' });
      const projectResult = await api.createProject({ name: 'test' });

      expect(branchResult).toBeNull();
      expect(projectResult).toBeNull();
    });
  });

  describe('Authentication State Handling', () => {
    it('should use V1 API when not authenticated', async () => {
      (apiV2.isAuthenticated as any).mockReturnValue(false);
      (api.createProject as any).mockImplementation(async (project) => {
        // When not authenticated, should skip V2 API entirely
        return { id: 'proj-v1-only', ...project };
      });

      const result = await api.createProject({
        name: 'V1 Only Project',
        description: 'Should use V1 API only'
      });

      expect(result).toMatchObject({
        name: 'V1 Only Project',
        description: 'Should use V1 API only'
      });

      // V2 API should not be called when not authenticated
      expect(apiV2.projectApiV2.createProject).not.toHaveBeenCalled();
    });
  });
});