import React, { useEffect } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { api, Task } from '../services/api';
import { Loader2, CheckCircle2, XCircle, RotateCcw, Clock, StopCircle, Trash2, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';

interface TaskSidebarProps {
  onRestore: (task: Task) => void;
  className?: string;
}

export const TaskSidebar: React.FC<TaskSidebarProps> = ({ onRestore, className }) => {
  const { tasks, fetchTasks, pollTasks, cancelTask, deleteTask, activeTaskId, setActiveTask, hasMore, loadMoreTasks, isLoading } = useTaskStore();

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    const hasRunning = tasks.some(t => ['PENDING', 'RUNNING'].includes(t.status));
    if (hasRunning) {
      pollTasks();
    }
  }, [tasks, pollTasks]);

  const handleRestore = (task: Task) => {
    onRestore(task);
  };

  const handleCancel = async (e: React.MouseEvent, task: Task) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to cancel this task?')) {
      await cancelTask(task.task_id);
    }
  };

  const handleDelete = async (e: React.MouseEvent, task: Task) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this task?')) {
      await deleteTask(task.task_id);
    }
  };

  return (
    <div className={clsx("w-80 bg-zinc-900 border-l border-zinc-800 flex flex-col h-full", className)}>
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-100">History</h2>
        <span className="text-xs text-zinc-500">{tasks.length} tasks</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {tasks.map((task) => (
          <div
            key={task.task_id}
            onClick={() => setActiveTask(task.task_id)}
            className={clsx(
              "group relative p-3 rounded-lg border transition-all cursor-pointer hover:bg-zinc-800/50",
              activeTaskId === task.task_id
                ? "bg-zinc-800 border-yellow-500/50"
                : "bg-zinc-900 border-zinc-800"
            )}
          >
            <div className="flex justify-between items-start gap-3">
              {/* Status Icon */}
              <div className="mt-1">
                {task.status === 'RUNNING' || task.status === 'PENDING' ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                ) : task.status === 'COMPLETED' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : task.status === 'CANCELLED' ? (
                    <StopCircle className="w-4 h-4 text-zinc-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-200 line-clamp-2 mb-1 font-medium">{task.prompt}</p>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock size={12} />
                  <span>{new Date(task.created_at).toLocaleTimeString()}</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                    {task.model?.toLowerCase().includes('seedream')
                      ? String((task.params as any)?.size || 'auto')
                      : task.resolution}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                 {['PENDING', 'RUNNING'].includes(task.status) ? (
                    <button
                        onClick={(e) => handleCancel(e, task)}
                        className="p-1.5 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 rounded transition-colors"
                        title="Cancel"
                    >
                        <StopCircle size={14} />
                    </button>
                 ) : (
                    <>
                    <button
                        onClick={(e) => { e.stopPropagation(); handleRestore(task); }}
                        className="p-1.5 hover:bg-yellow-500/20 text-zinc-400 hover:text-yellow-400 rounded transition-colors"
                        title="Restore Parameters"
                    >
                        <RotateCcw size={14} />
                    </button>
                    <button
                        onClick={(e) => handleDelete(e, task)}
                        className="p-1.5 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 rounded transition-colors"
                        title="Delete Task"
                    >
                        <Trash2 size={14} />
                    </button>
                    </>
                 )}
              </div>
            </div>

            {/* Thumbnail if completed */}
            {task.status === 'COMPLETED' && task.image_url && (
              <div className="mt-3 relative aspect-video rounded overflow-hidden bg-black/50 border border-zinc-800">
                <img
                  src={api.getImageUrl(task.image_url)}
                  alt="Thumbnail"
                  className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                  loading="lazy"
                />
              </div>
            )}
            
            {/* Error Message */}
            {task.status === 'FAILED' && (
                <div className="mt-2 text-xs text-red-400 bg-red-950/30 p-2 rounded border border-red-900/50">
                    {task.error_msg || "Generation failed"}
                </div>
            )}
          </div>
        ))}

        {tasks.length === 0 && !isLoading && (
          <div className="text-center py-10 text-zinc-600 text-sm">
            No tasks found
          </div>
        )}

        {hasMore && tasks.length > 0 && (
          <button 
            onClick={() => loadMoreTasks()}
            disabled={isLoading}
            className="w-full py-3 text-sm text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors flex items-center justify-center gap-2 mt-2"
          >
            {isLoading ? <Loader2 className="animate-spin w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {isLoading ? "Loading..." : "Load More"}
          </button>
        )}

        {!hasMore && tasks.length > 0 && (
          <div className="text-center py-4 text-xs text-zinc-600">
            No more tasks
          </div>
        )}
      </div>
    </div>
  );
};
