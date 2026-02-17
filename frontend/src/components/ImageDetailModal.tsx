import React from 'react';
import { X, Calendar, Image as ImageIcon, Layers, Monitor } from 'lucide-react';
import { ImageRecord, api } from '../services/api';

interface ImageDetailModalProps {
  image: ImageRecord | null;
  onClose: () => void;
}

export const ImageDetailModal: React.FC<ImageDetailModalProps> = ({ image, onClose }) => {
  if (!image) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="relative bg-zinc-900 border border-zinc-800 rounded-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col md:flex-row shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 bg-black/50 rounded-full text-white hover:bg-white/20 transition-colors"
        >
          <X size={20} />
        </button>

        {/* Main Image */}
        <div className="flex-1 bg-black flex items-center justify-center p-4 min-h-[300px] md:min-h-[400px] relative">
          <img 
            src={api.getImageUrl(image.image_url)} 
            alt={image.prompt} 
            className="max-w-full max-h-[80vh] object-contain"
          />
        </div>

        {/* Details Sidebar */}
        <div className="w-full md:w-96 bg-zinc-900 p-6 flex flex-col gap-6 overflow-y-auto border-l border-zinc-800">
          <div>
            <h3 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
              <ImageIcon size={16} /> Prompt
            </h3>
            <p className="text-zinc-100 text-sm leading-relaxed whitespace-pre-wrap font-light">
              {image.prompt}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-1 flex items-center gap-2">
                <Layers size={16} /> Aspect Ratio
              </h3>
              <p className="text-zinc-200 text-sm">{image.aspect_ratio || "1:1"}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-1 flex items-center gap-2">
                <Monitor size={16} /> Resolution
              </h3>
              <p className="text-zinc-200 text-sm">{image.resolution || "1K"}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-1 flex items-center gap-2">
                <Calendar size={16} /> Date
              </h3>
              <p className="text-zinc-200 text-sm">{new Date(image.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          {image.reference_images && image.reference_images.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-3">Reference Images</h3>
              <div className="grid grid-cols-3 gap-2">
                {image.reference_images.map((ref, idx) => (
                  <div key={idx} className="aspect-square rounded-md overflow-hidden border border-zinc-700">
                    <img 
                      src={api.getImageUrl(ref)} 
                      alt={`Reference ${idx + 1}`} 
                      className="w-full h-full object-cover"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
