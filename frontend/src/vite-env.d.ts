/// <reference types="vite/client" />

interface Window {
  riftBuddy?: {
    onRequestAdvice: (callback: () => void) => () => void;
    onToggleLanguage: (callback: () => void) => () => void;
  };
}
