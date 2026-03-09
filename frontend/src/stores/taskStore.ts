import { create } from 'zustand';
import { Task, api, GenerateOptions } from '../services/api';

interface TaskState {
  tasks: Task[];
  isLoading: boolean;
  activeTaskId: string | null;
  hasMore: boolean;
  fetchTasks: () => Promise<void>;
  loadMoreTasks: () => Promise<void>;
  addTask: (prompt: string, images: File[], options: GenerateOptions) => Promise<void>;
  cancelTask: (taskId: string) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  pollTasks: () => void;
  stopPolling: () => void;
  setActiveTask: (taskId: string | null) => void;
}

export const useTaskStore = create<TaskState>((set, get) => {
  let pollInterval: NodeJS.Timeout | null = null;

  return {
    tasks: [],
    isLoading: false,
    activeTaskId: null,
    hasMore: true,

    fetchTasks: async () => {
      set({ isLoading: true });
      try {
        const tasks = await api.getTasks(50, 0);
        set({ tasks, isLoading: false, hasMore: tasks.length === 50 });
      } catch (error) {
        console.error('Failed to fetch tasks:', error);
        set({ isLoading: false });
      }
    },

    loadMoreTasks: async () => {
      const state = get();
      if (!state.hasMore || state.isLoading) return;
      
      set({ isLoading: true });
      try {
        const currentCount = state.tasks.length;
        const newTasks = await api.getTasks(50, currentCount);
        set({ 
          tasks: [...state.tasks, ...newTasks], 
          isLoading: false, 
          hasMore: newTasks.length === 50 
        });
      } catch (error) {
        console.error('Failed to load more tasks:', error);
        set({ isLoading: false });
      }
    },

    addTask: async (prompt, images, options) => {
      try {
        const newTask = await api.generateImage(prompt, images, options);
        set((state) => ({ tasks: [newTask, ...state.tasks] }));
        get().pollTasks();
      } catch (error) {
        console.error('Failed to create task:', error);
        throw error;
      }
    },

    cancelTask: async (taskId) => {
      try {
        await api.cancelTask(taskId);
        set((state) => ({
          tasks: state.tasks.map((t) =>
            t.task_id === taskId ? { ...t, status: 'CANCELLED' } : t
          ),
        }));
      } catch (error) {
        console.error('Failed to cancel task:', error);
      }
    },

    deleteTask: async (taskId) => {
      try {
        await api.deleteTask(taskId);
        set((state) => ({
          tasks: state.tasks.filter((t) => t.task_id !== taskId),
          activeTaskId: state.activeTaskId === taskId ? null : state.activeTaskId
        }));
      } catch (error) {
        console.error('Failed to delete task:', error);
      }
    },
    
    setActiveTask: (taskId) => {
        set({ activeTaskId: taskId });
    },

    pollTasks: () => {
      if (pollInterval) return;

      const checkStatus = async () => {
        const state = get();
        const pendingTasks = state.tasks.filter((t) => 
          t.status === 'PENDING' || t.status === 'RUNNING'
        );

        if (pendingTasks.length === 0) {
          get().stopPolling();
          return;
        }

        // Refresh list
        try {
            const updatedTasks = await api.getTasks(50, 0);
            
            // Merge updated tasks with existing tasks to preserve pagination
            const currentTasksMap = new Map(state.tasks.map(t => [t.task_id, t]));
            const updatedTasksMap = new Map(updatedTasks.map(t => [t.task_id, t]));
            
            // Update existing tasks
            const newTaskList = state.tasks.map(t => updatedTasksMap.get(t.task_id) || t);
            
            // Add new tasks that weren't in the list
            const completelyNew = updatedTasks.filter(t => !currentTasksMap.has(t.task_id));
            
            set({ tasks: [...completelyNew, ...newTaskList] });
        } catch(e) {
            console.error("Polling error", e);
        }
      };

      // Poll every 2 seconds
      pollInterval = setInterval(checkStatus, 2000);
    },

    stopPolling: () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    },
  };
});
