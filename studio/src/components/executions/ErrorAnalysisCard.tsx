import { AlertTriangle, Copy, Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

interface ErrorAnalysisCardProps {
  statusMessage: string;
  affectedSpanIds?: string[];
}

interface ParsedError {
  exceptionType: string;
  rootCause: string;
  fullMessage: string;
}

/**
 * Parse error message to extract structured information
 * Example input: "ServiceResponseException("<class 'agent_framework.openai._chat_client.OpenAIChatClient'> service failed to complete the prompt: AsyncCompletions.create() got an unexpected keyword argument 'conversation_id'")"
 */
function parseErrorMessage(message: string): ParsedError {
  const fullMessage = message;
  
  // Extract exception type
  const exceptionTypeMatch = message.match(/^(\w+)\(/);
  const exceptionType = exceptionTypeMatch ? exceptionTypeMatch[1] : 'UnknownError';
  
  // Extract root cause (last meaningful part of the error message)
  // Remove the exception wrapper and get the core message
  let rootCause = message;
  
  // Remove outer exception wrapper like ServiceResponseException("...")
  const innerMatch = message.match(/\w+\("(.*?)"\)(?:\))?$/);
  if (innerMatch) {
    rootCause = innerMatch[1];
  }
  
  // Clean up class references
  rootCause = rootCause
    .replace(/<class '[^']+'>\\s*/g, '')
    .replace(/<class '[^']+'>\\s*/g, '')
    .replace(/\\n/g, '\n')
    .trim();
  
  return {
    exceptionType,
    rootCause,
    fullMessage,
  };
}

export function ErrorAnalysisCard({ statusMessage, affectedSpanIds = [] }: ErrorAnalysisCardProps) {
  const [copied, setCopied] = useState(false);
  
  const parsedError = parseErrorMessage(statusMessage);
  
  const handleCopyError = async () => {
    try {
      await navigator.clipboard.writeText(statusMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy error message', err);
    }
  };
  
  return (
    <Card className="p-4 border-red-200 bg-gradient-to-r from-red-50 to-red-50/50">
      <div className="space-y-3">
        {/* Header with icon */}
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 bg-red-100 rounded-lg flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-red-900 mb-1">Execution Failed</div>
            <div className="text-xs text-red-700 bg-red-100 px-2 py-1 rounded w-fit">
              Status: ERROR
            </div>
          </div>
        </div>

        {/* Exception Type */}
        <div className="bg-white rounded border border-red-200 p-2.5">
          <div className="text-xs font-semibold text-red-700 mb-1">Exception Type</div>
          <code className="text-sm font-mono text-red-900 break-all">
            {parsedError.exceptionType}
          </code>
        </div>

        {/* Root Cause */}
        <div className="bg-white rounded border border-red-200 p-2.5">
          <div className="text-xs font-semibold text-red-700 mb-1">Root Cause</div>
          <p className="text-sm text-red-900 break-words font-mono leading-relaxed whitespace-pre-wrap">
            {parsedError.rootCause}
          </p>
        </div>

        {/* Affected Spans */}
        {affectedSpanIds.length > 0 && (
          <div className="bg-white rounded border border-red-200 p-2.5">
            <div className="text-xs font-semibold text-red-700 mb-1.5">Affected Spans</div>
            <div className="space-y-1">
              {affectedSpanIds.map((spanId) => (
                <div key={spanId} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-600 flex-shrink-0" />
                  <code className="text-xs font-mono text-red-900 break-all">
                    {spanId}
                  </code>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyError}
            className="border-red-200 hover:bg-red-100 text-red-700"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 mr-1" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 mr-1" />
                Copy Error
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-red-200 hover:bg-red-100 text-red-700 ml-auto"
            disabled
            title="Coming soon - View stack trace in debug panel"
          >
            View Stack Trace
          </Button>
        </div>
      </div>
    </Card>
  );
}
