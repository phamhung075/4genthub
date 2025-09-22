import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface CascadeState {
  branches: Record<string, any>;
  tasks: Record<string, any>;
  projects: Record<string, any>;
  subtasks: Record<string, any>;
  contexts: Record<string, any>;
  lastUpdated: string | null;
}

const initialState: CascadeState = {
  branches: {},
  tasks: {},
  projects: {},
  subtasks: {},
  contexts: {},
  lastUpdated: null,
};

const cascadeSlice = createSlice({
  name: 'cascade',
  initialState,
  reducers: {
    updateFromWebSocket: (state, action: PayloadAction<{
      branches?: any[];
      tasks?: any[];
      projects?: any[];
      subtasks?: any[];
      contexts?: any[];
    }>) => {
      const { branches, tasks, projects, subtasks, contexts } = action.payload;

      // Update branches
      if (branches?.length) {
        branches.forEach(branch => {
          if (branch.id) {
            state.branches[branch.id] = branch;
          }
        });
      }

      // Update tasks
      if (tasks?.length) {
        tasks.forEach(task => {
          if (task.id) {
            state.tasks[task.id] = task;
          }
        });
      }

      // Update projects
      if (projects?.length) {
        projects.forEach(project => {
          if (project.id) {
            state.projects[project.id] = project;
          }
        });
      }

      // Update subtasks
      if (subtasks?.length) {
        subtasks.forEach(subtask => {
          if (subtask.id) {
            state.subtasks[subtask.id] = subtask;
          }
        });
      }

      // Update contexts
      if (contexts?.length) {
        contexts.forEach(context => {
          if (context.id) {
            state.contexts[context.id] = context;
          }
        });
      }

      state.lastUpdated = new Date().toISOString();
    },

    updateBranch: (state, action: PayloadAction<any>) => {
      const branch = action.payload;
      if (branch.id) {
        state.branches[branch.id] = branch;
        state.lastUpdated = new Date().toISOString();
      }
    },

    updateTask: (state, action: PayloadAction<any>) => {
      const task = action.payload;
      if (task.id) {
        state.tasks[task.id] = task;
        state.lastUpdated = new Date().toISOString();
      }
    },

    updateProject: (state, action: PayloadAction<any>) => {
      const project = action.payload;
      if (project.id) {
        state.projects[project.id] = project;
        state.lastUpdated = new Date().toISOString();
      }
    },

    removeBranch: (state, action: PayloadAction<string>) => {
      delete state.branches[action.payload];
      state.lastUpdated = new Date().toISOString();
    },

    removeTask: (state, action: PayloadAction<string>) => {
      delete state.tasks[action.payload];
      state.lastUpdated = new Date().toISOString();
    },

    removeProject: (state, action: PayloadAction<string>) => {
      delete state.projects[action.payload];
      state.lastUpdated = new Date().toISOString();
    },

    clearCascadeData: (state) => {
      state.branches = {};
      state.tasks = {};
      state.projects = {};
      state.subtasks = {};
      state.contexts = {};
      state.lastUpdated = null;
    },
  },
});

export const {
  updateFromWebSocket,
  updateBranch,
  updateTask,
  updateProject,
  removeBranch,
  removeTask,
  removeProject,
  clearCascadeData,
} = cascadeSlice.actions;

export default cascadeSlice.reducer;

// Selectors
export const selectCascadeState = (state: { cascade: CascadeState }) => state.cascade;
export const selectBranches = (state: { cascade: CascadeState }) => state.cascade.branches;
export const selectTasks = (state: { cascade: CascadeState }) => state.cascade.tasks;
export const selectProjects = (state: { cascade: CascadeState }) => state.cascade.projects;
export const selectSubtasks = (state: { cascade: CascadeState }) => state.cascade.subtasks;
export const selectContexts = (state: { cascade: CascadeState }) => state.cascade.contexts;
export const selectBranchById = (state: { cascade: CascadeState }, id: string) => state.cascade.branches[id];
export const selectTaskById = (state: { cascade: CascadeState }, id: string) => state.cascade.tasks[id];
export const selectProjectById = (state: { cascade: CascadeState }, id: string) => state.cascade.projects[id];