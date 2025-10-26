import { Card } from '@/components/ui/card';
import type { ConversationMessage } from '@/types';
import type { ElementType } from 'react';
import { Bot, MessageCircle, User } from 'lucide-react';

interface ConversationTimelineProps {
  messages: ConversationMessage[];
}

const roleStyles: Record<string, { icon: ElementType; label: string; badgeClass: string }> = {
  user: {
    icon: User,
    label: 'User',
    badgeClass: 'bg-blue-100 text-blue-700 border-blue-200',
  },
  assistant: {
    icon: Bot,
    label: 'Assistant',
    badgeClass: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  },
  system: {
    icon: MessageCircle,
    label: 'System',
    badgeClass: 'bg-slate-200 text-slate-700 border-slate-300',
  },
};

export function ConversationTimeline({ messages }: ConversationTimelineProps) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">Conversation</h2>
        <span className="text-xs text-muted-foreground">
          {messages.length} message{messages.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="space-y-4">
        {messages.map((message, index) => {
          const roleInfo = roleStyles[message.role] ?? roleStyles.system;
          const Icon = roleInfo.icon;
          const timeStamp = message.timestamp
            ? new Date(message.timestamp).toLocaleString()
            : null;

          return (
            <div key={`${message.role}-${index}`} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                  <Icon className="w-5 h-5 text-muted-foreground" />
                </div>
                {index < messages.length - 1 && (
                  <div className="flex-1 w-px bg-border my-1 grow" />
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full border ${roleInfo.badgeClass}`}
                  >
                    {roleInfo.label}
                  </span>
                  {message.name && (
                    <span className="text-xs text-muted-foreground">
                      {message.name}
                    </span>
                  )}
                  {timeStamp && (
                    <span className="text-xs text-muted-foreground">
                      {timeStamp}
                    </span>
                  )}
                </div>
                <div className="mt-2 whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm leading-relaxed text-foreground">
                  {message.content}
                </div>
                {message.metadata && (
                  <pre className="mt-2 rounded-md bg-background border border-border/60 p-3 text-xs text-muted-foreground overflow-x-auto">
                    {JSON.stringify(message.metadata, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
