import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface ImageRecord {
  id: string;
  image_url: string;
  prompt: string;
  created_at: string;
}

export interface GenerateResponse {
  success: boolean;
  image_url: string;
  prompt: string;
  created_at: string;
}

export const api = {
  async generateImage(prompt: string, image?: File): Promise<GenerateResponse> {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (image) {
      formData.append('image', image);
    }

    const response = await axios.post(`${API_BASE_URL}/generate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getHistory(): Promise<ImageRecord[]> {
    const response = await axios.get(`${API_BASE_URL}/history`);
    return response.data;
  },
  
  getImageUrl(path: string): string {
      if (path.startsWith('http')) return path;
      return `http://localhost:8000${path}`;
  }
};
