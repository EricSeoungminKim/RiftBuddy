export interface AdviceMessage {
  type: "advice";
  text: string;
  audio_error?: string | null;
  context: {
    health_percent: number;
    gold: number;
    level: number;
    game_time_minutes: number;
  };
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export interface TranscriptMessage {
  type: "transcript";
  text: string;
}

export interface ListeningMessage {
  type: "listening";
  text: string;
}

export interface ProactiveWarningMessage {
  type: "proactive_warning";
  text: string;
}

export type ServerMessage =
  | AdviceMessage
  | ErrorMessage
  | TranscriptMessage
  | ListeningMessage
  | ProactiveWarningMessage;
