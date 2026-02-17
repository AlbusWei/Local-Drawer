import React, { useCallback, useState, useEffect } from 'react';
import { Upload, X } from 'lucide-react';
import { clsx } from 'clsx';

interface MultiImageUploadProps {
  onImagesChange: (files: File[]) => void;
  selectedImages: File[];
}

export const MultiImageUpload: React.FC<MultiImageUploadProps> = ({ onImagesChange, selectedImages }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [previews, setPreviews] = useState<string[]>([]);

  useEffect(() => {
    // Cleanup old previews
    return () => {
      previews.forEach(url => URL.revokeObjectURL(url));
    };
  }, []);

  useEffect(() => {
    // Generate new previews when files change
    const newPreviews = selectedImages.map(file => URL.createObjectURL(file));
    setPreviews(newPreviews);
    
    return () => {
      newPreviews.forEach(url => URL.revokeObjectURL(url));
    };
  }, [selectedImages]);

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
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('image/'));
      if (newFiles.length > 0) {
        onImagesChange([...selectedImages, ...newFiles]);
      }
    }
  }, [selectedImages, onImagesChange]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
        const newFiles = Array.from(e.target.files);
        onImagesChange([...selectedImages, ...newFiles]);
    }
  };

  const removeImage = (index: number) => {
    const newImages = [...selectedImages];
    newImages.splice(index, 1);
    onImagesChange(newImages);
  };

  return (
    <div className="w-full space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={clsx(
          "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer min-h-[160px] flex flex-col items-center justify-center gap-4",
          isDragging
            ? "border-blue-500 bg-blue-500/10"
            : "border-zinc-700 hover:border-zinc-500 bg-zinc-900/50"
        )}
      >
        <input
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          id="image-upload"
          onChange={handleFileSelect}
        />
        <label htmlFor="image-upload" className="cursor-pointer flex flex-col items-center gap-2 w-full h-full">
          <Upload className="w-8 h-8 text-zinc-400" />
          <div className="text-zinc-400">
            <span className="font-medium text-zinc-200">Click to upload</span> or drag and drop
          </div>
          <p className="text-xs text-zinc-500">Supports multiple images (Max 14)</p>
        </label>
      </div>

      {selectedImages.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {previews.map((preview, index) => (
            <div key={index} className="relative group aspect-square rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900">
              <img src={preview} alt={`Upload ${index}`} className="w-full h-full object-cover" />
              <button
                onClick={() => removeImage(index)}
                className="absolute top-1 right-1 p-1 bg-black/60 rounded-full hover:bg-red-500/80 transition-colors text-white opacity-0 group-hover:opacity-100"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      
      {selectedImages.length > 0 && (
          <div className="text-xs text-zinc-500 text-right">
              {selectedImages.length} images selected
          </div>
      )}
    </div>
  );
};
