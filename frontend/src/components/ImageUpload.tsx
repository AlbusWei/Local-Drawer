import React, { useCallback, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { clsx } from 'clsx';

interface ImageUploadProps {
  onImageSelect: (file: File | null) => void;
  selectedImage: File | null;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageSelect, selectedImage }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        handleFileSelect(file);
      }
    }
  }, []);

  const handleFileSelect = (file: File) => {
    onImageSelect(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    onImageSelect(null);
    setPreview(null);
  };

  return (
    <div className="w-full">
      {preview ? (
        <div className="relative group rounded-xl overflow-hidden border border-zinc-800 bg-zinc-900">
          <img src={preview} alt="Upload preview" className="w-full h-64 object-contain" />
          <button
            onClick={clearImage}
            className="absolute top-2 right-2 p-1 bg-black/50 rounded-full hover:bg-black/70 transition-colors text-white"
          >
            <X size={20} />
          </button>
        </div>
      ) : (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={clsx(
            "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer min-h-[200px] flex flex-col items-center justify-center gap-4",
            isDragging
              ? "border-blue-500 bg-blue-500/10"
              : "border-zinc-700 hover:border-zinc-500 bg-zinc-900/50"
          )}
        >
          <input
            type="file"
            accept="image/*"
            className="hidden"
            id="image-upload"
            onChange={(e) => {
              if (e.target.files?.[0]) {
                handleFileSelect(e.target.files[0]);
              }
            }}
          />
          <label htmlFor="image-upload" className="cursor-pointer flex flex-col items-center gap-2 w-full h-full">
            <Upload className="w-10 h-10 text-zinc-400" />
            <div className="text-zinc-400">
              <span className="font-medium text-zinc-200">Click to upload</span> or drag and drop
            </div>
            <p className="text-xs text-zinc-500">SVG, PNG, JPG or GIF</p>
          </label>
        </div>
      )}
    </div>
  );
};
