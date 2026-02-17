import { useState, useEffect } from 'react';
import { MultiImageUpload } from './components/MultiImageUpload';
import { Gallery } from './components/Gallery';
import { AdvancedSettings } from './components/AdvancedSettings';
import { ImageDetailModal } from './components/ImageDetailModal';
import { TaskSidebar } from './components/TaskSidebar';
import { api, ImageRecord, Task } from './services/api';
import { Loader2, Sparkles, Image as ImageIcon } from 'lucide-react';
import { useTaskStore } from './stores/taskStore';

function App() {
  const [prompt, setPrompt] = useState('');
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [resolution, setResolution] = useState('1K');
  const [history, setHistory] = useState<ImageRecord[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<ImageRecord | null>(null);
  
  const { addTask, isLoading } = useTaskStore();

  useEffect(() => {
    // Adapter to fetch completed tasks for the gallery
    loadHistory();
    const interval = setInterval(loadHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadHistory = async () => {
    try {
      const tasks = await api.getTasks(50, 0);
      const completedTasks: ImageRecord[] = tasks
        .filter(t => t.status === 'COMPLETED' && t.image_url)
        .map(t => ({
            id: t.task_id,
            image_url: t.image_url!,
            prompt: t.prompt,
            created_at: t.created_at,
            aspect_ratio: t.aspect_ratio,
            resolution: t.resolution,
            reference_images: t.reference_images.map(r => r.url)
        }));
      setHistory(completedTasks);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    try {
      await addTask(prompt, selectedImages, { aspectRatio, resolution });
      setPrompt('');
      setSelectedImages([]);
      // Optional: Don't reset settings to allow repeated generation
    } catch (error) {
      console.error('Generation failed:', error);
      alert('Failed to start generation task.');
    }
  };

  const handleRestore = async (task: Task) => {
    setPrompt(task.prompt);
    setAspectRatio(task.aspect_ratio);
    setResolution(task.resolution);
    
    // Restore Reference Images
    if (task.reference_images && task.reference_images.length > 0) {
        const files: File[] = [];
        for (const ref of task.reference_images) {
            try {
                const file = await api.downloadImageAsFile(ref.url, ref.original_name || 'reference.jpg');
                files.push(file);
            } catch (e) {
                console.error("Failed to restore image", ref.url, e);
            }
        }
        setSelectedImages(files);
    } else {
        setSelectedImages([]);
    }
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      {/* Sidebar */}
      <TaskSidebar 
        onRestore={handleRestore} 
        className="flex-shrink-0"
      />

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-6xl mx-auto space-y-8">
          {/* Header */}
          <header className="flex items-center gap-3 pb-6 border-b border-zinc-800">
            <div className="p-2 bg-yellow-500/10 rounded-lg">
              <Sparkles className="w-6 h-6 text-yellow-500" />
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-yellow-200 to-yellow-500 bg-clip-text text-transparent">
              Nano Banana Pro
            </h1>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column: Input Area */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-zinc-900/50 p-6 rounded-2xl border border-zinc-800 space-y-6">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <ImageIcon className="w-5 h-5 text-zinc-400" />
                  Create
                </h2>
                
                <div className="space-y-2">
                   <label className="text-sm font-medium text-zinc-400">Reference Images</label>
                   <MultiImageUpload
                      selectedImages={selectedImages}
                      onImagesChange={setSelectedImages}
                    />
                </div>

                <div className="space-y-2">
                  <label htmlFor="prompt" className="text-sm font-medium text-zinc-400">
                    Prompt
                  </label>
                  <textarea
                    id="prompt"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe what you want to generate..."
                    className="w-full h-32 bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 resize-none transition-all"
                  />
                </div>

                <AdvancedSettings 
                  aspectRatio={aspectRatio}
                  onAspectRatioChange={setAspectRatio}
                  resolution={resolution}
                  onResolutionChange={setResolution}
                />

                <button
                  onClick={handleGenerate}
                  disabled={isLoading || !prompt.trim()}
                  className="w-full py-4 bg-yellow-500 hover:bg-yellow-400 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-yellow-500/20"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Generate Image (Async)
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Right Column: Gallery */}
            <div className="lg:col-span-7 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-zinc-200">History</h2>
                <span className="text-sm text-zinc-500">{history.length} completed</span>
              </div>
              
              <Gallery 
                images={history} 
                onSelect={setSelectedRecord}
              />
            </div>
          </div>
        </div>

        <ImageDetailModal 
          image={selectedRecord} 
          onClose={() => setSelectedRecord(null)} 
        />
      </div>
    </div>
  );
}

export default App;
