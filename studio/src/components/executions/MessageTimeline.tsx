import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Message, ChildSpan } from '@/types';
import type { ElementType } from 'react';
import { Bot, MessageCircle, User, Copy, Check, FileText, Code, Wrench, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageTimelineProps {
  messages: Message[];
  direction: 'input' | 'output';
  title?: string;
  childSpans?: ChildSpan[]; // Priority 2: Pass child spans for attribution
}

const roleStyles: Record<string, { icon: ElementType; label: string; iconColor: string; borderColor: string }> = {
  user: {
    icon: User,
    label: 'User',
    iconColor: 'text-blue-600',
    borderColor: 'border-blue-200',
  },
  assistant: {
    icon: Bot,
    label: 'Assistant',
    iconColor: 'text-foreground',
    borderColor: 'border-border',
  },
  system: {
    icon: MessageCircle,
    label: 'System',
    iconColor: 'text-muted-foreground',
    borderColor: 'border-muted',
  },
  tool: {
    icon: Wrench,
    label: 'Tool',
    iconColor: 'text-orange-600',
    borderColor: 'border-orange-200',
  },
};

export function MessageTimeline({ messages, direction, title, childSpans }: MessageTimelineProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [showRaw, setShowRaw] = useState<Record<string, boolean>>({});

  // Priority 2: Create span lookup map for quick access
  const spanMap = useMemo(() => {
    if (!childSpans) return new Map();
    const map = new Map<string, ChildSpan>();
    childSpans.forEach(span => map.set(span.span_id, span));
    return map;
  }, [childSpans]);

  // Priority 2: Count spans by type for labeling (e.g., "Chat #1", "Chat #2")
  const spanTypeCounters = useMemo(() => {
    const counters = new Map<string, Map<string, number>>(); // type -> span_id -> index
    if (!childSpans) return counters;
    
    const typeCounts = new Map<string, number>();
    childSpans
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
      .forEach(span => {
        const count = (typeCounts.get(span.type) ?? 0) + 1;
        typeCounts.set(span.type, count);
        
        if (!counters.has(span.type)) {
          counters.set(span.type, new Map());
        }
        counters.get(span.type)!.set(span.span_id, count);
      });
    
    return counters;
  }, [childSpans]);

  const getSpanLabel = (spanId: string, spanType: string): string => {
    const typeMap = spanTypeCounters.get(spanType);
    if (!typeMap) return spanType;
    const index = typeMap.get(spanId);
    if (!index) return spanType;
    
    // Capitalize type and add number
    const capitalizedType = spanType.charAt(0).toUpperCase() + spanType.slice(1);
    return `${capitalizedType} #${index}`;
  };

  const getSpanTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      agent: 'bg-blue-50 text-blue-700 border-blue-200',
      chat: 'bg-purple-50 text-purple-700 border-purple-200',
      tool: 'bg-orange-50 text-orange-700 border-orange-200',
      llm: 'bg-green-50 text-green-700 border-green-200',
    };
    return colors[type] ?? 'bg-gray-50 text-gray-700 border-gray-200';
  };

  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (err) {
      console.error('Failed to copy message', err);
    }
  };

  const toggleRaw = (key: string) => {
    setShowRaw(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // Detect if content looks like markdown
  const hasMarkdownSyntax = (content: string): boolean => {
    const markdownPatterns = [
      /^#{1,6}\s/m,           // Headers
      /\*\*.*\*\*/,           // Bold
      /\*.*\*/,               // Italic
      /\[.*\]\(.*\)/,         // Links
      /^[-*+]\s/m,            // Unordered lists
      /^\d+\.\s/m,            // Ordered lists
      /```/,                  // Code blocks
      /`[^`]+`/,              // Inline code
      /^>\s/m,                // Blockquotes
      /\|.*\|/,               // Tables
    ];
    
    return markdownPatterns.some(pattern => pattern.test(content));
  };

  const defaultTitle = direction === 'input' ? 'Input Messages' : 'Output Messages';
  const displayTitle = title ?? defaultTitle;

  return (
    <Card className="p-5 border-border/80">
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-muted-foreground" />
            {displayTitle}
          </h2>
        </div>
        <Badge variant="secondary" className="text-xs">
          {messages.length} message{messages.length === 1 ? '' : 's'}
        </Badge>
      </div>

      <div className="space-y-4">
        {messages.map((message, index) => {
          const roleInfo = roleStyles[message.role] ?? roleStyles.system;
          const Icon = roleInfo.icon;
          const isCopied = copiedIndex === index;

          return (
            <div key={`${message.role}-${message.msg_index}-${index}`} className="flex gap-4 group">
              {/* Avatar Column */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div className={`w-9 h-9 rounded-full bg-muted/50 border flex items-center justify-center ${roleInfo.borderColor}`}>
                  <Icon className={`w-4 h-4 ${roleInfo.iconColor}`} />
                </div>
                {index < messages.length - 1 && (
                  <div className="flex-1 w-px bg-border/40 my-2 min-h-[16px]" />
                )}
              </div>

              {/* Message Content Column */}
              <div className="flex-1 min-w-0">
                {/* Message Header */}
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className="text-xs font-semibold text-foreground">
                    {roleInfo.label}
                  </span>
                  
                  {/* Priority 2: Span Attribution Badge - Only show for assistant messages */}
                  {message.role === 'assistant' && message.span_id && message.span_type && (
                    <Badge 
                      variant="outline" 
                      className={`text-xs flex items-center gap-1 ${getSpanTypeColor(message.span_type)}`}
                      title={`Generated by span: ${message.span_id.slice(0, 8)}`}
                    >
                      <Zap className="w-2.5 h-2.5" />
                      {message.agent_name || getSpanLabel(message.span_id, message.span_type)}
                    </Badge>
                  )}
                  
                  {/* Tool Call Badge - Show tool name if this message has a tool call */}
                  {message.parts.some(p => p.type === 'tool_call') && (
                    <Badge 
                      variant="outline" 
                      className="text-xs flex items-center gap-1 bg-orange-50 text-orange-700 border-orange-200"
                    >
                      <Wrench className="w-2.5 h-2.5" />
                      {message.parts.find(p => p.type === 'tool_call')?.name || 'Tool'}
                    </Badge>
                  )}
                </div>

                {/* Message Parts */}
                <div className="space-y-2">
                  {message.parts.map((part, partIndex) => {
                    const hasMarkdown = part.content ? hasMarkdownSyntax(part.content) : false;
                    const partKey = `${message.msg_index}-${partIndex}`;
                    const isPartRaw = showRaw[partKey] ?? false;

                    return (
                      <div key={partIndex} className="relative rounded-lg border bg-card p-4">

                        {/* Render based on part type */}
                        {part.type === 'tool_call' ? (
                          // Tool Call rendering
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Wrench className="w-4 h-4 text-orange-600" />
                              <span className="font-mono text-sm font-semibold text-orange-900">
                                {part.name || 'Unknown Tool'}
                              </span>
                            </div>
                            {part.arguments && (
                              <div className="mt-2">
                                <div className="text-xs text-muted-foreground mb-1">Arguments:</div>
                                <div className="bg-slate-950 text-slate-200 p-2 rounded font-mono text-xs overflow-x-auto">
                                  {JSON.stringify(JSON.parse(part.arguments), null, 2)}
                                </div>
                              </div>
                            )}
                            {part.id && (
                              <div className="text-xs text-muted-foreground mt-1">
                                ID: <code className="font-mono">{part.id}</code>
                              </div>
                            )}
                          </div>
                        ) : part.type === 'tool_call_response' ? (
                          // Tool Response rendering
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Check className="w-4 h-4 text-green-600" />
                              <span className="text-sm font-semibold text-green-900">Tool Result</span>
                            </div>
                            {part.response && (
                              <div className="mt-2">
                                <div className="bg-green-50 border border-green-200 p-2 rounded text-sm">
                                  {typeof part.response === 'string' && part.response.startsWith('"') ? 
                                    JSON.parse(part.response) : part.response}
                                </div>
                              </div>
                            )}
                            {part.id && (
                              <div className="text-xs text-muted-foreground mt-1">
                                ID: <code className="font-mono">{part.id}</code>
                              </div>
                            )}
                          </div>
                        ) : part.content ? (
                          // Text content rendering
                          <>
                            {isPartRaw || !hasMarkdown ? (
                              <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                                {part.content}
                              </div>
                            ) : (
                              <div className="prose prose-sm max-w-none dark:prose-invert prose-pre:bg-slate-950 prose-pre:text-slate-200">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                  {part.content}
                                </ReactMarkdown>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="text-sm text-muted-foreground italic">
                            No content available
                          </div>
                        )}
                        
                        {/* Action Buttons */}
                        {part.content && (
                          <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {hasMarkdown && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 bg-white/80 hover:bg-white"
                              onClick={() => toggleRaw(partKey)}
                              title={isPartRaw ? "Render as markdown" : "Show raw text"}
                            >
                              {isPartRaw ? (
                                <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                              ) : (
                                <Code className="w-3.5 h-3.5 text-muted-foreground" />
                              )}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 bg-white/80 hover:bg-white"
                            onClick={() => handleCopy(part.content || '', index)}
                          >
                            {isCopied ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                          </Button>
                        </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
