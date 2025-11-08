import { useRef, forwardRef, useImperativeHandle, useEffect, useMemo } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import { cn } from '@/lib/utils';

export type EditorMarker = {
  message: string;
  severity: 'error' | 'warning' | 'info';
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
};

interface RichTemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  readOnly?: boolean;
  markers?: EditorMarker[];
  suggestions?: string[]; // variable name suggestions
}

export interface RichTemplateEditorRef {
  insertAtCursor: (text: string) => void;
  focus: () => void;
}

let jinjaRegistered = false;

export const RichTemplateEditor = forwardRef<RichTemplateEditorRef, RichTemplateEditorProps>(
  ({ value, onChange, placeholder, className, readOnly = false, markers = [], suggestions = [] }, ref) => {
    const monaco = useMonaco();
    const editorRef = useRef<any>(null);

    // Register Jinja2 language + theme once
    useEffect(() => {
      if (!monaco || jinjaRegistered) return;

      monaco.languages.register({ id: 'jinja2' });
      monaco.languages.setMonarchTokensProvider('jinja2', {
        defaultToken: '',
        tokenPostfix: '.jinja2',
        brackets: [],
        keywords: [
          'if','else','elif','for','endfor','endif','set','include','filter','endfilter','macro','endmacro',
          'block','endblock','extends','import','from','with','endwith','raw','endraw'
        ],
        tokenizer: {
          root: [
            [/\{#/, { token: 'comment.jinja', next: '@comment' }],
            [/\{\{[-\s]?/, { token: 'delimiter.jinja', next: '@variable' }],
            [/\{%[-\s]?/, { token: 'delimiter.jinja', next: '@tag' }],
            [/[^\{]+/, ''],
            [/./, '']
          ],
          comment: [
            [/#\}/, { token: 'comment.jinja', next: '@root' }],
            [/./, 'comment.jinja']
          ],
          variable: [
            [/[-\s]?\}\}/, { token: 'delimiter.jinja', next: '@root' }],
            [/\b(true|false|none)\b/, 'keyword'],
            [/\b\d+(?:\.\d+)?\b/, 'number'],
            [/\b[a-zA-Z_][\w\.]*\b/, 'variable.jinja'],
            [/\|/, 'operator.jinja'],
            [/"[^"]*"|'[^']*'/, 'string'],
            [/[,\.:\(\)\[\]]/, 'delimiter'],
            [/\s+/, 'white']
          ],
          tag: [
            [/[-\s]?%\}/, { token: 'delimiter.jinja', next: '@root' }],
            [/\b(if|else|elif|for|endfor|endif|set|include|filter|endfilter|macro|endmacro|block|endblock|extends|import|from|with|endwith|raw|endraw)\b/, 'keyword.jinja'],
            [/\b[a-zA-Z_][\w]*\b/, 'identifier'],
            [/"[^"]*"|'[^']*'/, 'string'],
            [/[,\.:\(\)\[\]]/, 'delimiter'],
            [/\s+/, 'white']
          ]
        }
      } as any);

      monaco.editor.defineTheme('dakora', {
        base: 'vs',
        inherit: true,
        rules: [
          { token: 'keyword.jinja', foreground: '8B5CF6', fontStyle: 'bold' },
          { token: 'variable.jinja', foreground: '1A73E8' },
          { token: 'delimiter.jinja', foreground: '6B7280' },
          { token: 'comment.jinja', foreground: '9CA3AF', fontStyle: 'italic' }
        ],
        colors: {}
      } as any);

      jinjaRegistered = true;
    }, [monaco]);

    // Register simple completion provider for variable suggestions
    useEffect(() => {
      if (!monaco) return;
      const disposable = monaco.languages.registerCompletionItemProvider('jinja2', {
        provideCompletionItems: () => {
          const items = (suggestions || []).map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Variable,
            insertText: name,
          }));
          return { suggestions: items } as any;
        },
      });
      return () => disposable.dispose();
    }, [monaco, JSON.stringify(suggestions)]);

    // Expose ref actions
    useImperativeHandle(ref, () => ({
      insertAtCursor: (text: string) => {
        if (!editorRef.current || readOnly || !monaco) return;
        const editor = editorRef.current;
        const model = editor.getModel();
        const position = editor.getPosition();
        if (!model || !position) return;

        // Determine if we need surrounding newlines similar to previous behavior
        const value = model.getValue();
        const offset = model.getOffsetAt(position);
        const before = offset > 0 ? value[offset - 1] : '';
        const after = offset < value.length ? value[offset] : '';
        const needsNewlineBefore = before !== '' && before !== '\n';
        const needsNewlineAfter = after !== '' && after !== '\n';
        const textToInsert = (needsNewlineBefore ? '\n' : '') + text + (needsNewlineAfter ? '\n' : '');

        editor.executeEdits('insert-text', [
          {
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column,
            },
            text: textToInsert,
            forceMoveMarkers: true,
          },
        ]);
        editor.focus();
      },
      focus: () => editorRef.current?.focus()
    }));

    // Apply markers
    useEffect(() => {
      if (!monaco || !editorRef.current) return;
      const model = editorRef.current.getModel();
      if (!model) return;

      const owner = 'dakora-template-validation';
      const monacoMarkers = markers.map((m) => ({
        message: m.message,
        severity: m.severity === 'error' ? monaco.MarkerSeverity.Error : m.severity === 'warning' ? monaco.MarkerSeverity.Warning : monaco.MarkerSeverity.Info,
        startLineNumber: Math.max(1, m.startLineNumber),
        startColumn: Math.max(1, m.startColumn),
        endLineNumber: Math.max(m.startLineNumber, m.endLineNumber),
        endColumn: Math.max(m.startColumn, m.endColumn),
      }));
      monaco.editor.setModelMarkers(model, owner, monacoMarkers as any);
    }, [markers, monaco]);

    const editorClass = useMemo(
      () => cn('min-h-[300px] h-[320px] font-mono text-sm relative', className),
      [className]
    );
    const showPlaceholder = !value && placeholder;

    return (
      <div className={editorClass} style={{ minHeight: '300px', overflow: 'hidden' }}>
        {showPlaceholder && (
          <div className="pointer-events-none absolute left-4 top-3 text-sm text-muted-foreground/70 z-10">
            {placeholder}
          </div>
        )}
        <Editor
          height="100%"
          defaultLanguage="jinja2"
          theme="dakora"
          value={value}
          onChange={(val) => onChange(val ?? '')}
          options={{
            readOnly,
            minimap: { enabled: false },
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            quickSuggestions: false,
            tabSize: 2,
            fontSize: 13,
            fixedOverflowWidgets: true,
          }}
          onMount={(editor) => {
            editorRef.current = editor;
          }}
        />
      </div>
    );
  }
);

RichTemplateEditor.displayName = 'RichTemplateEditor';
