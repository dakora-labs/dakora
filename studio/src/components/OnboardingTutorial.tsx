import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from './ui/dialog';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { Sparkles, Settings, Download, FileText, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface OnboardingTutorialProps {
  open: boolean;
  onClose: () => void;
  projectSlug: string;
}

const STEPS = [
  {
    id: 0,
    title: 'Welcome to Dakora',
    description: 'Your control plane for production LLM applications',
    icon: Sparkles,
    content: () => (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          Ship with confidence. Let's get you started in just a few quick steps.
        </p>
        <div className="bg-muted/50 rounded-lg p-4 space-y-2">
          <p className="text-sm font-medium">What you'll learn:</p>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• How to create API keys</li>
            <li>• Installing the Python client</li>
            <li>• Creating your first prompt</li>
          </ul>
        </div>
      </div>
    )
  },
  {
    id: 1,
    title: 'Create Your First API Key',
    description: 'API keys allow you to authenticate and use Dakora programmatically.',
    icon: Settings,
    content: (projectSlug: string) => (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Go to Settings to generate your first API key. You'll need this to authenticate your client.
        </p>
        <Link to={`/project/${projectSlug}/settings`}>
          <Button variant="outline" className="w-full">
            <Settings className="w-4 h-4 mr-2" />
            Go to Settings
          </Button>
        </Link>
      </div>
    )
  },
  {
    id: 2,
    title: 'Install the Client',
    description: 'Install the Dakora Python client to interact with your prompts.',
    icon: Download,
    content: () => (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Install the Dakora client using pip:
        </p>
        <div className="relative">
          <pre className="bg-muted p-4 rounded-lg text-sm font-mono overflow-x-auto">
            pip install dakora-client[maf]
          </pre>
          <Button
            size="sm"
            variant="ghost"
            className="absolute top-2 right-2"
            onClick={() => {
              navigator.clipboard.writeText('pip install dakora-client[maf]');
            }}
          >
            Copy
          </Button>
        </div>
      </div>
    )
  },
  {
    id: 3,
    title: 'Create Your First Prompt',
    description: 'Start building AI-powered applications with prompt templates.',
    icon: FileText,
    content: (projectSlug: string) => (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Create your first prompt template and start executing LLM calls.
        </p>
        <div className="flex flex-col gap-2">
          <Link to={`/project/${projectSlug}/prompts/new`}>
            <Button variant="outline" className="w-full">
              <FileText className="w-4 h-4 mr-2" />
              Create Prompt
            </Button>
          </Link>
          <a
            href="http://docs.dakora.io"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full"
          >
            <Button variant="ghost" className="w-full">
              <ExternalLink className="w-4 h-4 mr-2" />
              View Documentation
            </Button>
          </a>
        </div>
      </div>
    )
  }
];

export function OnboardingTutorial({ open, onClose, projectSlug }: OnboardingTutorialProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleClose = () => {
    if (dontShowAgain) {
      localStorage.setItem('dakora_onboarding_completed', 'true');
    }
    onClose();
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const step = STEPS[currentStep];
  const Icon = step.icon;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            {currentStep === 0 ? (
              <div className="w-10 h-10 rounded-md bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-lg">D</span>
              </div>
            ) : (
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Icon className="w-5 h-5 text-primary" />
              </div>
            )}
            <DialogTitle className="text-xl">{step.title}</DialogTitle>
          </div>
          <DialogDescription>{step.description}</DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {step.content(projectSlug)}
        </div>

        <div className="flex items-center justify-center gap-2 mb-4">
          {STEPS.map((_, index) => (
            <div
              key={index}
              className={cn(
                "h-1.5 rounded-full transition-all",
                index === currentStep
                  ? "w-8 bg-primary"
                  : "w-1.5 bg-muted"
              )}
            />
          ))}
        </div>

        <div className="flex items-center space-x-2 mb-4">
          <Checkbox
            id="dontShowAgain"
            checked={dontShowAgain}
            onCheckedChange={(checked: boolean) => setDontShowAgain(checked)}
          />
          <Label
            htmlFor="dontShowAgain"
            className="text-sm font-normal cursor-pointer"
          >
            Don't show this again
          </Label>
        </div>

        <DialogFooter className="flex-row justify-between sm:justify-between">
          <Button
            variant="ghost"
            onClick={handleClose}
          >
            {currentStep === 0 ? 'Dismiss' : 'Skip'}
          </Button>
          <div className="flex gap-2">
            {currentStep > 0 && (
              <Button
                variant="outline"
                onClick={handlePrevious}
              >
                Previous
              </Button>
            )}
            <Button onClick={handleNext}>
              {currentStep === 0 ? 'Continue' : currentStep === STEPS.length - 1 ? 'Get Started' : 'Next'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}