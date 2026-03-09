import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface ReferenceImage {
  hash: string;
  url: string;
  original_name: string;
  mime_type: string;
}

// Keeping ImageRecord for backward compatibility with Gallery/Modal components
// In a real refactor, we should merge Task and ImageRecord concepts
export interface ImageRecord {
  id: string;
  image_url: string;
  prompt: string;
  created_at: string;
  aspect_ratio?: string;
  resolution?: string;
  reference_images?: string[];
}

export interface Task {
  task_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  prompt: string;
  model: string;
  image_url?: string;
  image_urls?: string[] | null;
  created_at: string;
  error_msg?: string;
  aspect_ratio: string;
  resolution: string;
  params?: Record<string, unknown> | null;
  reference_images: ReferenceImage[];
}

export interface GenerateOptions {
  model?: string;
  aspectRatio?: string;
  resolution?: string;
  webSearch?: boolean;
  seedream?: {
    size?: string;
    quality?: string;
    n?: number;
    promptPriority?: string;
    outputFormat?: string;
    responseFormat?: string;
    webSearch?: boolean;
  };
}

export const api = {
  async generateImage(prompt: string, images: File[] = [], options: GenerateOptions = {}): Promise<Task> {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('model', options.model || 'gemini-3.1-flash-image-preview');
    formData.append('aspect_ratio', options.aspectRatio || "1:1");
    formData.append('resolution', options.resolution || "1K");
    if (options.webSearch) formData.append('web_search', 'true');

    if (options.seedream) {
      if (options.seedream.size) formData.append('size', options.seedream.size);
      if (options.seedream.quality) formData.append('quality', options.seedream.quality);
      if (typeof options.seedream.n === 'number') formData.append('n', String(options.seedream.n));
      if (options.seedream.promptPriority) formData.append('prompt_priority', options.seedream.promptPriority);
      if (options.seedream.outputFormat) formData.append('output_format', options.seedream.outputFormat);
      if (options.seedream.responseFormat) formData.append('response_format', options.seedream.responseFormat);
      if (options.seedream.webSearch) formData.append('web_search', 'true');
    }
    
    if (images.length > 0) {
      images.forEach((image) => {
        formData.append('images', image);
      });
    }

    const response = await axios.post(`${API_BASE_URL}/generate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getTasks(limit: number = 50, offset: number = 0): Promise<Task[]> {
    const response = await axios.get(`${API_BASE_URL}/tasks`, {
      params: { limit, offset }
    });
    return response.data;
  },

  async getTask(taskId: string): Promise<Task> {
    const response = await axios.get(`${API_BASE_URL}/tasks/${taskId}`);
    return response.data;
  },

  // Backward compatibility wrapper for history
  async getHistory(): Promise<ImageRecord[]> {
      const tasks = await this.getTasks(50, 0);
      return tasks
        .filter(t => t.status === 'COMPLETED' && (t.image_urls?.length || t.image_url))
        .flatMap((t) => {
          const urls = (t.image_urls && t.image_urls.length > 0)
            ? t.image_urls
            : (t.image_url ? [t.image_url] : []);

          return urls.map((url, idx) => ({
            id: `${t.task_id}:${idx + 1}`,
            image_url: url,
            prompt: t.prompt,
            created_at: t.created_at,
            aspect_ratio: t.aspect_ratio,
            resolution: t.resolution,
            reference_images: t.reference_images.map(r => r.url)
          }));
        });
  },

  async cancelTask(taskId: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/tasks/${taskId}/cancel`);
  },

  async deleteTask(taskId: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/tasks/${taskId}`);
  },
  
  getImageUrl(path: string): string {
      if (!path) return '';
      if (path.startsWith('http')) return path;
      return `http://localhost:8000${path}`;
  },

  async downloadImageAsFile(url: string, filename: string): Promise<File> {
      const response = await axios.get(this.getImageUrl(url), { responseType: 'blob' });
      return new File([response.data], filename, { type: response.headers['content-type'] });
  }
};
