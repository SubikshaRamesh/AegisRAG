export interface Source {
  type: "pdf" | "image" | "audio" | "video" | "docx" | "unknown" | string;
  source: string;
  score: number;
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  sources: Source[];
}

export interface UploadResponse {
  status: string;
  filename: string;
  file_type: string;
  chunks_extracted: number;
  chunks_added: number;
  duplicates_skipped: number;
  processing_time_seconds: number;
  message: string;
}

export interface HealthStatus {
  status: string;
  text_vectors: number;
  image_vectors: number;
}

export interface StatusResponse {
  status: string;
  text_embedder: string;
  clip_embedder: string;
  llm_model: string;
  text_vectors: number;
  image_vectors: number;
  vector_dim: {
    text: number;
    image: number;
  };
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: number;
}

export interface HistoryResponse {
  status: string;
  session_id: string;
  count: number;
  history: HistoryMessage[];
}

class ApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`/api${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  async askQuestion(question: string, sessionId: string): Promise<QueryResponse> {
    return this.request("/query", {
      method: "POST",
      body: JSON.stringify({ question, session_id: sessionId }),
    });
  }

  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.detail || "Upload failed"));
          }
        } catch (error) {
          reject(new Error("Upload failed"));
        }
      };

      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.send(formData);
    });
  }

  async healthCheck(): Promise<HealthStatus> {
    return this.request("/health");
  }

  async getStatus(): Promise<StatusResponse> {
    return this.request("/status");
  }

  async getHistory(sessionId: string): Promise<HistoryResponse> {
    return this.request(`/history/${encodeURIComponent(sessionId)}`);
  }
}

export const api = new ApiService();