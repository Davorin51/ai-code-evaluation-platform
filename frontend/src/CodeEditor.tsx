import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });
export default function CodeEditor({
  code,
  onChange,
  readOnly = false,
}: {
  code: string;
  onChange?: (code: string) => void;
  readOnly?: boolean;
}) {
  return (
    <Editor
      height="340px"
      language="python"
      theme="vs-dark"
      value={code}
      onChange={(v) => onChange?.(v ?? "")}
      loading={<p className="muted">Loading local Python editor…</p>}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        lineHeight: 22,
        padding: { top: 16 },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: "on",
        tabSize: 4,
        accessibilitySupport: "on",
        ariaLabel: "Python candidate solution editor",
      }}
    />
  );
}
