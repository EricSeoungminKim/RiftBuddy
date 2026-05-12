export interface AdviceMessage {
  type: "advice";
  text: string;
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

export interface ProactiveWarningMessage {
  type: "proactive_warning";
  text: string;
}

export interface GameStateMessage {
  type: "game_state";
  [key: string]: unknown;
}

export interface GameEndMessage {
  type: "game_end";
}

export type ServerMessage =
  | AdviceMessage
  | ErrorMessage
  | TranscriptMessage
  | ProactiveWarningMessage
  | GameStateMessage
  | GameEndMessage;
