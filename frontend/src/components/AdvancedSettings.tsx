import React from 'react';

interface AdvancedSettingsProps {
  aspectRatio: string;
  onAspectRatioChange: (ratio: string) => void;
  resolution: string;
  onResolutionChange: (resolution: string) => void;
  showWebSearch?: boolean;
  webSearch?: boolean;
  onWebSearchChange?: (enabled: boolean) => void;
}

export const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({ 
  aspectRatio, 
  onAspectRatioChange,
  resolution,
  onResolutionChange,
  showWebSearch = false,
  webSearch = false,
  onWebSearchChange
}) => {
  const ratios = ["1:1", "16:9", "4:3", "3:4", "9:16"];
  const resolutions = ["1K", "2K", "4K"];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-zinc-400">Aspect Ratio</label>
        <div className="flex gap-2 flex-wrap">
          {ratios.map((ratio) => (
            <button
              key={ratio}
              onClick={() => onAspectRatioChange(ratio)}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors border ${
                aspectRatio === ratio
                  ? "bg-white text-black border-white"
                  : "bg-zinc-800 text-zinc-300 border-zinc-700 hover:border-zinc-500"
              }`}
            >
              {ratio}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-zinc-400">Resolution</label>
        <div className="flex gap-2 flex-wrap">
          {resolutions.map((res) => (
            <button
              key={res}
              onClick={() => onResolutionChange(res)}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors border ${
                resolution === res
                  ? "bg-white text-black border-white"
                  : "bg-zinc-800 text-zinc-300 border-zinc-700 hover:border-zinc-500"
              }`}
            >
              {res}
            </button>
          ))}
        </div>
      </div>

      {showWebSearch && (
        <label className="flex items-center gap-2 text-sm text-zinc-300 select-none">
          <input
            type="checkbox"
            checked={webSearch}
            onChange={(e) => onWebSearchChange?.(e.target.checked)}
            className="h-4 w-4 accent-yellow-500"
          />
          Web Search
        </label>
      )}
    </div>
  );
};
