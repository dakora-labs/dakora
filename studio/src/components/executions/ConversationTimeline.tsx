import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ConversationMessage } from '@/types';
import type { ElementType } from 'react';
import { Bot, MessageCircle, User, Users, Copy, Check, FileText, Code } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ConversationTimelineProps {
  messages: ConversationMessage[];
  currentAgentId?: string | null;
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
};

export function ConversationTimeline({ messages }: ConversationTimelineProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [showRaw, setShowRaw] = useState<Record<number, boolean>>({});

  // Extract unique agents from message metadata
  const agentsInConversation = messages
    .filter((msg) => msg.metadata?.agent_id)
    .reduce((acc, msg) => {
      const agentId = msg.metadata?.agent_id as string;
      if (!acc.includes(agentId)) {
        acc.push(agentId);
      }
      return acc;
    }, [] as string[]);

  const isMultiAgent = agentsInConversation.length > 1;

  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (err) {
      console.error('Failed to copy message', err);
    }
  };

  const toggleRaw = (index: number) => {
    setShowRaw(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Detect if content looks like markdown
  const hasMarkdownSyntax = (content: string): boolean => {
    // Check for common markdown patterns
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

  return (
    <Card className="p-5 border-border/80">
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-border/60">
        <div>
          <h2 className="text-base font-semibold flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-muted-foreground" />
            Conversation
          </h2>
          {isMultiAgent && (
            <div className="flex items-center gap-2 mt-2">
              <Users className="w-4 h-4 text-purple-600" />
              <p className="text-xs text-purple-700 font-medium">
                Multi-Agent Session · {agentsInConversation.length} agents
              </p>
            </div>
          )}
        </div>
        <Badge variant="secondary" className="text-xs">
          {messages.length} message{messages.length === 1 ? '' : 's'}
        </Badge>
      </div>

      <div className="space-y-4">
        {messages.map((message, index) => {
          const roleInfo = roleStyles[message.role] ?? roleStyles.system;
          const Icon = roleInfo.icon;
          const timeStamp = message.timestamp
            ? new Date(message.timestamp).toLocaleString()
            : null;
          
          const messageAgentId = message.metadata?.agent_id as string | undefined;
          const showAgentBadge = isMultiAgent && messageAgentId;
          const isCopied = copiedIndex === index;
          const isRaw = showRaw[index] ?? false;
          const hasMarkdown = hasMarkdownSyntax(message.content);

          return (
            <div key={`${message.role}-${index}`} className="flex gap-4 group">
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
                  {message.name && (
                    <span className="text-xs text-muted-foreground">
                      · {message.name}
                    </span>
                  )}
                  {showAgentBadge && (
                    <Badge 
                      variant="outline" 
                      className="text-xs bg-purple-50 text-purple-700 border-purple-200 font-mono"
                    >
                      {messageAgentId}
                    </Badge>
                  )}
                  {timeStamp && (
                    <span className="text-xs text-muted-foreground/60">
                      · {timeStamp}
                    </span>
                  )}
                </div>

                {/* Message Content */}
                <div className="relative rounded-lg border bg-card p-4 min-w-0">
                  {isRaw || !hasMarkdown ? (
                    <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground break-words">
                      {message.content}
                    </div>
                  ) : (
                    <div className="prose prose-sm max-w-none dark:prose-invert prose-pre:bg-slate-950 prose-pre:text-slate-200 prose-pre:overflow-x-auto prose-pre:max-w-full prose-code:break-words">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
                  
                  {/* Action Buttons */}
                  <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {hasMarkdown && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 bg-white/80 hover:bg-white"
                        onClick={() => toggleRaw(index)}
                        title={isRaw ? "Render as markdown" : "Show raw text"}
                      >
                        {isRaw ? (
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
                      onClick={() => handleCopy(message.content, index)}
                    >
                      {isCopied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Metadata */}
                {message.metadata && Object.keys(message.metadata).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground select-none">
                      View metadata
                    </summary>
                    <pre className="mt-2 rounded-md bg-slate-950 border border-slate-800 p-3 text-xs text-slate-200 overflow-x-auto font-mono">
                      {JSON.stringify(message.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
