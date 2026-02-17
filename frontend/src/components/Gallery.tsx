import React from 'react';
import { ImageRecord, api } from '../services/api';

interface GalleryProps {
  images: ImageRecord[];
  onSelect: (image: ImageRecord) => void;
}

export const Gallery: React.FC<GalleryProps> = ({ images, onSelect }) => {
  if (images.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500">
        No generated images yet. Start creating!
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {images.map((image) => (
        <div 
          key={image.id} 
          className="group relative aspect-square bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800 cursor-pointer"
          onClick={() => onSelect(image)}
        >
          <img
            src={api.getImageUrl(image.image_url)}
            alt={image.prompt}
            className="w-full h-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
            <p className="text-white text-sm line-clamp-2">{image.prompt}</p>
            <span className="text-zinc-400 text-xs mt-1">
              {new Date(image.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};
