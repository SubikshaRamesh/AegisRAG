import { FileText } from "lucide-react";

interface SourceLinkProps {
  filename: string;
  type?: string;
  score?: number;
  onPreview?: (filename: string) => void;
}

export const SourceLink = ({ filename, type, score, onPreview }: SourceLinkProps) => {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (onPreview) {
      onPreview(filename);
    }
  };

  return (
    <div className="rounded-xl border border-border/80 bg-muted/40 p-3 text-sm">
      <button
        onClick={handleClick}
        className="flex items-center gap-2 text-foreground hover:text-primary transition-colors duration-200 group cursor-pointer w-full"
        title={`Preview ${filename}`}
      >
        <FileText className="w-4 h-4 text-primary flex-shrink-0" />
        <span className="truncate group-hover:underline text-left">{filename}</span>
      </button>
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
        {type && <span className="uppercase">{type}</span>}
        {score !== undefined && <span>Score {score.toFixed(1)}%</span>}
      </div>
    </div>
  );
};
