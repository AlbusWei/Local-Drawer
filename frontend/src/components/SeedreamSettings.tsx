import React from 'react';

export interface SeedreamParams {
  size: string;
  quality: string;
  n: number;
  promptPriority: string;
  outputFormat: string;
  responseFormat: string;
  webSearch: boolean;
}

interface SeedreamSettingsProps {
  params: SeedreamParams;
  onChange: (next: SeedreamParams) => void;
}

export const SeedreamSettings: React.FC<SeedreamSettingsProps> = ({ params, onChange }) => {
  const qualityOptions = ['auto', '0.5K', '1K', '2K', '3K', '4K'];
  const promptPriorityOptions = ['standard', 'quality'];
  const outputFormatOptions = ['jpeg', 'png', 'webp'];
  const responseFormatOptions = ['url', 'b64_json'];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-zinc-400">Size</label>
        <input
          value={params.size}
          onChange={(e) => onChange({ ...params, size: e.target.value })}
          placeholder="auto 或 1024x1024"
          className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-400">Quality</label>
          <select
            value={params.quality}
            onChange={(e) => onChange({ ...params, quality: e.target.value })}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
          >
            {qualityOptions.map((q) => (
              <option key={q} value={q}>{q}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-400">Count (n)</label>
          <input
            type="number"
            min={1}
            max={15}
            value={params.n}
            onChange={(e) => onChange({ ...params, n: Math.max(1, Math.min(15, Number(e.target.value) || 1)) })}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-400">Prompt Priority</label>
          <select
            value={params.promptPriority}
            onChange={(e) => onChange({ ...params, promptPriority: e.target.value })}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
          >
            {promptPriorityOptions.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-400">Output Format</label>
          <select
            value={params.outputFormat}
            onChange={(e) => onChange({ ...params, outputFormat: e.target.value })}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
          >
            {outputFormatOptions.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-400">Response Format</label>
          <select
            value={params.responseFormat}
            onChange={(e) => onChange({ ...params, responseFormat: e.target.value })}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
          >
            {responseFormatOptions.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-zinc-300 select-none">
          <input
            type="checkbox"
            checked={params.webSearch}
            onChange={(e) => onChange({ ...params, webSearch: e.target.checked })}
            className="h-4 w-4 accent-yellow-500"
          />
          Web Search
        </label>
      </div>
    </div>
  );
};
