import { X } from "lucide-react";

interface FilePreviewModalProps {
  isOpen: boolean;
  filename: string;
  onClose: () => void;
}

const getFileExtension = (filename: string): string => {
  return filename.split(".").pop()?.toLowerCase() || "";
};

export const FilePreviewModal = ({
  isOpen,
  filename,
  onClose,
}: FilePreviewModalProps) => {
  if (!isOpen) return null;

  const ext = getFileExtension(filename);
  const apiPath = `/api/files/${encodeURIComponent(filename)}`;

  // Determine file type and render appropriate preview
  const renderPreview = () => {
    // PDF files
    if (ext === "pdf") {
      return (
        <iframe
          src={apiPath}
          title={filename}
          className="w-full h-full rounded-lg"
        />
      );
    }

    // Image files
    if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(ext)) {
      return (
        <img
          src={apiPath}
          alt={filename}
          className="max-w-full max-h-full object-contain rounded-lg"
        />
      );
    }

    // Audio files
    if (["mp3", "wav", "aac", "flac", "ogg", "m4a"].includes(ext)) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 p-8">
          <div className="w-24 h-24 rounded-full bg-accent flex items-center justify-center">
            <svg
              className="w-12 h-12 text-primary"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M18 3a1 1 0 00-1.196-.15l-1.559.987a2 2 0 01-2.29-.16l-.707-.707a1 1 0 00-1.414 1.414l.707.707a2 2 0 01.16 2.29l-.987 1.559A1 1 0 006 13h.01a6 6 0 0011.986 0H18a1 1 0 00.804-1.604l-.663-.663A2 2 0 0018 10V4a2 2 0 00-2-1h-2z" />
            </svg>
          </div>
          <audio
            controls
            src={apiPath}
            className="w-full max-w-md"
          />
          <p className="text-sm text-muted-foreground text-center">{filename}</p>
        </div>
      );
    }

    // Video files
    if (["mp4", "webm", "ogg", "avi", "mov", "mkv"].includes(ext)) {
      return (
        <video
          controls
          src={apiPath}
          className="w-full h-full rounded-lg object-contain"
        />
      );
    }

    // DOCX and unsupported formats
    return (
      <div className="flex flex-col items-center justify-center gap-6 p-8">
        <div className="w-24 h-24 rounded-full bg-accent flex items-center justify-center">
          <svg
            className="w-12 h-12 text-primary"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9 2a2 2 0 00-2 2v12a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-foreground mb-2">
            Preview not supported
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            Preview is not available for {ext.toUpperCase()} files.
            <br />
            Please download to view.
          </p>
        </div>
        <a
          href={apiPath}
          download
          className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
        >
          Download {ext.toUpperCase()}
        </a>
      </div>
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-foreground/50 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border">
            <h2 className="text-lg font-semibold text-foreground truncate flex-1">
              {filename}
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-lg transition-colors text-muted-foreground hover:text-foreground"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-4 flex items-center justify-center">
            {renderPreview()}
          </div>
        </div>
      </div>
    </>
  );
};
