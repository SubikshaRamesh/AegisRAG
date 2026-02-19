import { useState, useRef } from "react";
import {
  Upload,
  FileText,
  FileVideo,
  FileAudio,
  File,
  X,
  CheckCircle2,
  CloudUpload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";
import { extractErrorMessage } from "@/utils/errorHandler";

interface UploadedFile {
  id: number;
  name: string;
  size: string;
  type: string;
  status: "uploading" | "done" | "error";
  progress: number;
  message?: string;
}

const getFileIcon = (type: string) => {
  if (type.startsWith("video")) return FileVideo;
  if (type.startsWith("audio")) return FileAudio;
  if (type.includes("pdf") || type.includes("text") || type.includes("document"))
    return FileText;
  return File;
};

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
};

const UploadPage = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (fileList: FileList) => {
    const newFiles: UploadedFile[] = Array.from(fileList).map((f) => ({
      id: Date.now() + Math.random(),
      name: f.name,
      size: formatSize(f.size),
      type: f.type,
      status: "uploading" as const,
      progress: 0,
    }));
    setFiles((prev) => [...newFiles, ...prev]);

    newFiles.forEach((nf, index) => {
      const file = fileList[index];
      if (!file) return;

      api
        .uploadFile(file, (progress) => {
          setFiles((prev) =>
            prev.map((f) => (f.id === nf.id ? { ...f, progress } : f))
          );
        })
        .then((response) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === nf.id
                ? {
                    ...f,
                    status: "done",
                    progress: 100,
                    message: response.message,
                  }
                : f
            )
          );
        })
        .catch((error) => {
          const message = extractErrorMessage(error);
          setFiles((prev) =>
            prev.map((f) =>
              f.id === nf.id
                ? { ...f, status: "error", message, progress: 100 }
                : f
            )
          );
        });
    });
  };

  const removeFile = (id: number) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <CloudUpload className="w-6 h-6 text-primary" />
          Upload Files
        </h1>
        <p className="text-muted-foreground mt-1">
          Upload documents, audio, video, or text files for AI analysis
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
          dragOver
            ? "border-primary bg-accent scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-muted/50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        <div className="flex flex-col items-center gap-4">
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${
              dragOver ? "gradient-sky shadow-sky" : "bg-accent"
            }`}
          >
            <Upload
              className={`w-8 h-8 ${dragOver ? "text-primary-foreground" : "text-primary"}`}
            />
          </div>
          <div>
            <p className="text-lg font-semibold text-foreground">
              Drop files here or click to browse
            </p>
            <p className="text-muted-foreground mt-1">
              Supports PDF, DOCX, TXT, MP3, MP4, and more
            </p>
          </div>
        </div>
      </div>

      {/* Uploaded files */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground">
            Uploaded Files ({files.length})
          </h2>
          {files.map((file) => {
            const Icon = getFileIcon(file.type);
            return (
              <div
                key={file.id}
                className="flex items-center gap-4 p-4 bg-card border border-border rounded-xl shadow-card hover:shadow-card-hover transition-shadow duration-300"
              >
                <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{file.size}</p>
                  {file.status === "uploading" && (
                    <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full gradient-sky rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>
                {file.status === "done" ? (
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                ) : file.status === "error" ? (
                  <span className="text-xs text-rose-400">Failed</span>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    {Math.round(file.progress)}%
                  </span>
                )}
                <button
                  onClick={() => removeFile(file.id)}
                  className="text-muted-foreground hover:text-destructive transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
      {files.some((file) => file.message) && (
        <div className="space-y-2">
          {files
            .filter((file) => file.message)
            .slice(0, 4)
            .map((file) => (
              <div
                key={`msg-${file.id}`}
                className={`rounded-xl border px-4 py-2 text-xs ${
                  file.status === "error"
                    ? "border-rose-500/40 bg-rose-500/10 text-rose-200"
                    : "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                }`}
              >
                {file.name}: {file.message}
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default UploadPage;
