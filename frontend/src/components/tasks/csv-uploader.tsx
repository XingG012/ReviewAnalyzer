/** CSV 文件上传组件 — 拖拽上传 + 预览前 10 行 */

"use client";

import { FileText, Upload, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { uploadCSV } from "@/lib/api-client";
import type { UploadResponse } from "@/types";

interface Props {
  onUploaded: (result: UploadResponse) => void;
  onReset: () => void;
}

export function CsvUploader({ onUploaded, onReset }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".csv")) {
        setError("请上传 .csv 格式的文件");
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setError("文件大小不能超过 50MB");
        return;
      }
      setError(null);
      setUploading(true);
      try {
        const r = await uploadCSV(file);
        setResult(r);
        onUploaded(r);
      } catch (e) {
        setError(e instanceof Error ? e.message : "上传失败");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleReset = () => {
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
    onReset();
  };

  if (result) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-green-600" />
            <div>
              <p className="font-medium text-sm">{result.original_name}</p>
              <p className="text-xs text-muted-foreground">
                {(result.size_bytes / 1024).toFixed(0)} KB · {result.review_count} 条评论
              </p>
            </div>
          </div>
          <button onClick={handleReset} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        {result.preview_rows.length > 0 && (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b">
                  {Object.keys(result.preview_rows[0])
                    .slice(0, 5)
                    .map((k) => (
                      <th key={k} className="text-left p-1 font-medium text-muted-foreground">
                        {k}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {result.preview_rows.slice(0, 5).map((row, i) => (
                  <tr key={i} className="border-b border-muted/50">
                    {Object.values(row)
                      .slice(0, 5)
                      .map((v, j) => (
                        <td key={j} className="p-1 truncate max-w-[120px]">
                          {String(v)}
                        </td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
          dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"
        } ${uploading ? "opacity-50 pointer-events-none" : "cursor-pointer hover:border-primary/50"}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
        <p className="mt-2 text-sm">
          {uploading ? "上传中..." : "拖拽 CSV 文件到此处，或点击选择"}
        </p>
        <p className="text-xs text-muted-foreground mt-1">支持 .csv 格式，最大 50MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
