export interface Source {
  type: "pdf" | "image" | "audio" | "video" | "docx" | "unknown" | string;
  source: string;
  score: number;
}

export interface QueryResponse {
  chat_id: string;
  answer: string;
  confidence: number;
  sources: Source[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  sources?: Source[];
}

export interface ChatHistory {
  chat_id: string;
  messages: ChatMessage[];
}

export interface CreateChatResponse {
  chat_id: string;
  created_at: string;
}

export interface ConversationItem {
  chat_id: string;
  title: string;
  created_at: string;
}

export interface ListConversationsResponse {
  status: string;
  conversations: ConversationItem[];
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

export interface FileInventoryItem {
  file_name: string;
  total_chunks: number;
  first_ingested_timestamp: string;
  last_ingested_timestamp: string;
}

export interface FilesInventoryResponse {
  status: string;
  count: number;
  files: FileInventoryItem[];
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
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
      const message = error.detail || `API request failed: ${response.statusText}`;
      throw new ApiError(message, response.status);
    }

    return response.json();
  }

  async createChat(): Promise<CreateChatResponse> {
    return this.request("/chat/new", { method: "POST" });
  }

  async loadConversation(chatId: string): Promise<ChatHistory> {
    return this.request(`/history/${encodeURIComponent(chatId)}`);
  }

  async listConversations(limit: number = 50, offset: number = 0): Promise<ListConversationsResponse> {
    const query = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
    return this.request(`/history?${query}`);
  }

  async askQuestion(question: string, chatId: string): Promise<QueryResponse> {
    return this.request("/query", {
      method: "POST",
      body: JSON.stringify({ question, chat_id: chatId }),
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

  async getFiles(): Promise<FilesInventoryResponse> {
    return this.request("/files");
  }
}

export const api = new ApiService();