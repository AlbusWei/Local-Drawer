import { useState, useEffect } from 'react';
import { ImageUpload } from './components/ImageUpload';
import { Gallery } from './components/Gallery';
import { api, ImageRecord } from './services/api';
import { Loader2, Sparkles, Image as ImageIcon } from 'lucide-react';

function App() {
  const [prompt, setPrompt] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [history, setHistory] = useState<ImageRecord[]>([]);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await api.getHistory();
      setHistory(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setGeneratedImage(null);
    try {
      const response = await api.generateImage(prompt, selectedImage || undefined);
      if (response.success) {
        setGeneratedImage(api.getImageUrl(response.image_url));
        await loadHistory();
        // Optional: clear inputs
        // setPrompt('');
        // setSelectedImage(null);
      }
    } catch (error) {
      console.error('Generation failed:', error);
      alert('Failed to generate image. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 md:p-8 font-sans">
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Input Area */}
          <div className="space-y-6">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-zinc-400" />
                Input
              </h2>
              
              <ImageUpload
                selectedImage={selectedImage}
                onImageSelect={setSelectedImage}
              />

              <div className="space-y-2">
                <label htmlFor="prompt" className="text-sm font-medium text-zinc-400">
                  Prompt
                </label>
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe what you want to generate..."
                  className="w-full h-32 bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 resize-none transition-all"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="w-full py-4 bg-yellow-500 hover:bg-yellow-400 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate Image
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Column: Preview & History */}
          <div className="space-y-6">
            {/* Latest Result */}
            {generatedImage && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Result</h2>
                <div className="bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800">
                  <img
                    src={generatedImage}
                    alt="Generated result"
                    className="w-full h-auto object-contain max-h-[500px]"
                  />
                </div>
              </div>
            )}

            {/* Gallery */}
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-400">History</h2>
              <Gallery images={history} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
