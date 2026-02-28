declare module "react-speech-recognition" {
  export interface StartListeningOptions {
    continuous?: boolean;
    language?: string;
  }

  export interface UseSpeechRecognitionResult {
    transcript: string;
    interimTranscript: string;
    finalTranscript: string;
    listening: boolean;
    browserSupportsSpeechRecognition: boolean;
    browserSupportsContinuousListening?: boolean;
    isMicrophoneAvailable?: boolean;
    resetTranscript: () => void;
  }

  export interface UseSpeechRecognitionOptions {
    transcribing?: boolean;
    clearTranscriptOnListen?: boolean;
    commands?: unknown[];
  }

  export function useSpeechRecognition(
    options?: UseSpeechRecognitionOptions,
  ): UseSpeechRecognitionResult;

  export interface SpeechRecognitionController {
    startListening: (options?: StartListeningOptions) => Promise<void>;
    stopListening: () => Promise<void>;
    abortListening: () => Promise<void>;
    applyPolyfill: (polyfill: unknown) => void;
    removePolyfill: () => void;
    getRecognition: () => unknown | null;
  }

  const SpeechRecognition: SpeechRecognitionController;
  export default SpeechRecognition;
}
