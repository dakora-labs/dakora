import { useState, useRef } from 'react';
import { Bug, Upload, X } from 'lucide-react';
import * as Sentry from '@sentry/react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';

interface BugReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userEmail?: string;
}

const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED !== 'false';
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
const SENTRY_ENABLED = AUTH_REQUIRED && SENTRY_DSN;

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_FILE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];

export function BugReportDialog({ open, onOpenChange, userEmail }: BugReportDialogProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    const validFiles: File[] = [];
    const errors: string[] = [];

    for (const file of files) {
      if (!ALLOWED_FILE_TYPES.includes(file.type)) {
        errors.push(`${file.name}: Invalid file type. Please upload PNG, JPEG, GIF, or WebP images.`);
        continue;
      }

      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File too large. Maximum size is 5MB.`);
        continue;
      }

      if (screenshots.length + validFiles.length >= 3) {
        errors.push('Maximum 3 screenshots allowed.');
        break;
      }

      validFiles.push(file);
    }

    if (errors.length > 0) {
      toast({
        title: 'Some files could not be added',
        description: errors.join('\n'),
        variant: 'destructive',
      });
    }

    if (validFiles.length > 0) {
      setScreenshots([...screenshots, ...validFiles]);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveScreenshot = (index: number) => {
    setScreenshots(screenshots.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      toast({
        title: 'Missing information',
        description: 'Please provide both a title and description for the bug report.',
        variant: 'destructive',
      });
      return;
    }

    if (!SENTRY_ENABLED) {
      toast({
        title: 'Bug reporting unavailable',
        description: 'Bug reporting is only available in cloud mode with Sentry configured.',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const scope = Sentry.getCurrentScope();

      if (userEmail) {
        scope.setUser({
          email: userEmail,
          username: userEmail.split('@')[0],
        });
      }

      for (let i = 0; i < screenshots.length; i++) {
        const file = screenshots[i];
        const arrayBuffer = await file.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);

        scope.addAttachment({
          filename: `screenshot-${i + 1}-${file.name}`,
          data: uint8Array,
          contentType: file.type,
        });
      }

      Sentry.captureMessage(`Bug Report: ${title}`, {
        level: 'info',
        tags: {
          type: 'user_report',
          screenshots_count: screenshots.length.toString(),
        },
        contexts: {
          bug_report: {
            title,
            description,
            email: userEmail || undefined,
            user_agent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            screenshot_count: screenshots.length,
          },
        },
      });

      toast({
        title: 'Bug report submitted',
        description: 'Thank you for helping us improve Dakora. We will investigate this issue.',
      });

      setTitle('');
      setDescription('');
      setScreenshots([]);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to submit bug report:', error);
      toast({
        title: 'Failed to submit bug report',
        description: 'Please try again later or contact support directly.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setTitle('');
    setDescription('');
    setScreenshots([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center gap-2">
            <Bug className="w-5 h-5 text-destructive" />
            <DialogTitle>Report a Bug</DialogTitle>
          </div>
          <DialogDescription>
            Describe the issue you encountered and we'll investigate it. Your report will be sent to our error tracking system.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4 px-1 pr-3 overflow-y-auto flex-1 min-h-0">
          <div className="space-y-2">
            <Label htmlFor="bug-title">
              Title <span className="text-destructive">*</span>
            </Label>
            <Input
              id="bug-title"
              placeholder="Brief summary of the issue"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="bug-description">
              Description <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="bug-description"
              placeholder="What happened? What were you trying to do? Include steps to reproduce if possible..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={6}
              className="resize-none"
            />
          </div>

          <div className="space-y-2">
            <Label>Screenshots (optional)</Label>
            <div className="space-y-2">
              {screenshots.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {screenshots.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="relative group rounded-md border border-border overflow-hidden"
                    >
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Screenshot ${index + 1}`}
                        className="w-20 h-20 object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveScreenshot(index)}
                        className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ALLOWED_FILE_TYPES.join(',')}
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={screenshots.length >= 3 || !SENTRY_ENABLED}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={screenshots.length >= 3 || !SENTRY_ENABLED}
                  className="w-full"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  {screenshots.length === 0 ? 'Add Screenshots' : `Add More (${screenshots.length}/3)`}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Upload up to 3 screenshots (PNG, JPEG, GIF, WebP, max 5MB each)
              </p>
            </div>
          </div>

          {userEmail && (
            <div className="space-y-2">
              <Label>Your email</Label>
              <div className="px-3 py-2 rounded-md bg-muted text-sm text-muted-foreground">
                {userEmail}
              </div>
              <p className="text-xs text-muted-foreground">
                We'll use this to follow up if we need more information
              </p>
            </div>
          )}

          {!SENTRY_ENABLED && (
            <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
              Bug reporting is only available in cloud mode. For self-hosted deployments, please report issues on GitHub.
            </div>
          )}
        </div>

        <DialogFooter className="flex-shrink-0">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={!title.trim() || !description.trim() || isSubmitting || !SENTRY_ENABLED}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}