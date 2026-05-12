/// <reference types="vite/client" />

interface Window {
  riftBuddy?: {
    onRequestAdvice: (callback: () => void) => () => void;
    onRequestMatchup: (callback: () => void) => () => void;
    onRequestItems: (callback: () => void) => () => void;
    onRequestMacro: (callback: () => void) => () => void;
    onRequestVoiceQuestion: (callback: () => void) => () => void;
    onToggleLanguage: (callback: () => void) => () => void;
    onTabSwitch?: (callback: (tabIndex: number) => void) => () => void;
    onSettingsMode?: (callback: () => void) => () => void;
    onLeagueBounds?: (callback: (bounds: { x: number; y: number; width: number; height: number }) => void) => () => void;
    exitSettingsMode?: () => void;
  };
}
