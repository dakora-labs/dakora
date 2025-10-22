import { useRef, forwardRef, useImperativeHandle } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

interface RichTemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  readOnly?: boolean;
}

export interface RichTemplateEditorRef {
  insertAtCursor: (text: string) => void;
  focus: () => void;
}

export const RichTemplateEditor = forwardRef<RichTemplateEditorRef, RichTemplateEditorProps>(
  ({ value, onChange, placeholder, className, readOnly = false }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const insertAtCursor = (text: string) => {
      if (readOnly || !textareaRef.current) return;

      const textarea = textareaRef.current;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;

      // Insert at cursor position with newlines
      const needsNewlineBefore = start > 0 && value[start - 1] !== '\n';
      const needsNewlineAfter = end < value.length && value[end] !== '\n';

      const textToInsert = (needsNewlineBefore ? '\n' : '') + text + (needsNewlineAfter ? '\n' : '');
      const newValue = value.slice(0, start) + textToInsert + value.slice(end);

      onChange(newValue);

      // Set cursor position after inserted text
      setTimeout(() => {
        const newPosition = start + textToInsert.length;
        textarea.setSelectionRange(newPosition, newPosition);
        textarea.focus();
      }, 0);
    };

    useImperativeHandle(ref, () => ({
      insertAtCursor,
      focus: () => textareaRef.current?.focus()
    }));

    return (
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        readOnly={readOnly}
        className={cn(
          'min-h-[300px] font-mono text-sm resize-none',
          className
        )}
      />
    );
  }
);

RichTemplateEditor.displayName = 'RichTemplateEditor';