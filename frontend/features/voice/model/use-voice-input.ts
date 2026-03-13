"use client";

import * as React from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/errors";

import { transcribeAudio } from "@/features/voice/api/voice-api";

export type VoiceInputStatus = "idle" | "recording" | "transcribing";

interface UseVoiceInputOptions {
  t: (key: string, opts?: Record<string, unknown>) => string;
  onTranscription: (text: string) => void;
  language?: string;
}

interface RecordingFormat {
  extension: string;
  mimeType?: string;
}

const RECORDING_FORMAT_CANDIDATES: RecordingFormat[] = [
  { mimeType: "audio/webm;codecs=opus", extension: "webm" },
  { mimeType: "audio/webm", extension: "webm" },
  { mimeType: "audio/mp4", extension: "mp4" },
  { mimeType: "audio/ogg;codecs=opus", extension: "ogg" },
  { mimeType: "audio/ogg", extension: "ogg" },
];

function isVoiceInputSupported(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return Boolean(
    typeof navigator.mediaDevices?.getUserMedia === "function" &&
    typeof MediaRecorder !== "undefined",
  );
}

function isPermissionDenied(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    ["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(
      error.name,
    )
  );
}

function resolveRecordingFormat(): RecordingFormat {
  if (
    typeof window === "undefined" ||
    typeof MediaRecorder === "undefined" ||
    typeof MediaRecorder.isTypeSupported !== "function"
  ) {
    return { extension: "webm" };
  }

  return (
    RECORDING_FORMAT_CANDIDATES.find(
      (item) => item.mimeType && MediaRecorder.isTypeSupported(item.mimeType),
    ) || { extension: "webm" }
  );
}

function extensionFromMimeType(mimeType: string): string {
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("mpeg")) return "mp3";
  if (mimeType.includes("wav")) return "wav";
  return "webm";
}

export function useVoiceInput({
  t,
  onTranscription,
  language,
}: UseVoiceInputOptions) {
  const [status, setStatus] = React.useState<VoiceInputStatus>("idle");
  const isSupported = isVoiceInputSupported();

  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const mediaStreamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);
  const abortControllerRef = React.useRef<AbortController | null>(null);
  const skipNextTranscriptionRef = React.useRef(false);
  const isMountedRef = React.useRef(true);
  const onTranscriptionRef = React.useRef(onTranscription);

  React.useEffect(() => {
    onTranscriptionRef.current = onTranscription;
  }, [onTranscription]);

  const updateStatus = React.useCallback((nextStatus: VoiceInputStatus) => {
    if (isMountedRef.current) {
      setStatus(nextStatus);
    }
  }, []);

  const stopMediaTracks = React.useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }, []);

  const discardCurrentRecording = React.useCallback(() => {
    skipNextTranscriptionRef.current = true;

    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    } else {
      chunksRef.current = [];
      stopMediaTracks();
      mediaRecorderRef.current = null;
    }
  }, [stopMediaTracks]);

  const handleVoiceError = React.useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.message.trim()) {
        toast.error(error.message);
        return;
      }

      console.error("[VoiceInput] Voice input failed:", error);
      toast.error(t("hero.toasts.voiceInputFailed"));
    },
    [t],
  );

  const startRecording = React.useCallback(async () => {
    if (!isSupported) {
      toast.error(t("hero.toasts.voiceInputNotSupported"));
      return;
    }

    if (status !== "idle") {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const format = resolveRecordingFormat();
      const recorder = format.mimeType
        ? new MediaRecorder(stream, { mimeType: format.mimeType })
        : new MediaRecorder(stream);

      chunksRef.current = [];
      skipNextTranscriptionRef.current = false;
      mediaRecorderRef.current = recorder;
      mediaStreamRef.current = stream;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const shouldSkip = skipNextTranscriptionRef.current;
        skipNextTranscriptionRef.current = false;

        const recordedChunks = [...chunksRef.current];
        chunksRef.current = [];
        mediaRecorderRef.current = null;
        stopMediaTracks();

        if (shouldSkip) {
          updateStatus("idle");
          return;
        }

        const mimeType = recorder.mimeType || format.mimeType || "audio/webm";
        const blob = new Blob(recordedChunks, { type: mimeType });
        if (blob.size === 0) {
          updateStatus("idle");
          toast.error(t("hero.toasts.voiceInputFailed"));
          return;
        }

        const extension = extensionFromMimeType(mimeType);
        const file = new File([blob], `voice-input.${extension}`, {
          type: blob.type || mimeType,
        });

        updateStatus("transcribing");
        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        void transcribeAudio(file, {
          language,
          signal: abortController.signal,
        })
          .then((result) => {
            onTranscriptionRef.current(result.text);
          })
          .catch((error) => {
            if (abortController.signal.aborted) {
              return;
            }
            handleVoiceError(error);
          })
          .finally(() => {
            if (abortControllerRef.current === abortController) {
              abortControllerRef.current = null;
            }
            updateStatus("idle");
          });
      };

      recorder.start();
      updateStatus("recording");
    } catch (error) {
      stopMediaTracks();
      mediaRecorderRef.current = null;
      chunksRef.current = [];
      updateStatus("idle");

      if (isPermissionDenied(error)) {
        toast.error(t("hero.toasts.voiceInputPermissionDenied"));
        return;
      }

      handleVoiceError(error);
    }
  }, [
    handleVoiceError,
    isSupported,
    language,
    status,
    stopMediaTracks,
    t,
    updateStatus,
  ]);

  const stopRecording = React.useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return;
    }

    recorder.stop();
  }, []);

  const toggleRecording = React.useCallback(async () => {
    if (status === "transcribing") {
      return;
    }

    if (status === "recording") {
      stopRecording();
      return;
    }

    await startRecording();
  }, [startRecording, status, stopRecording]);

  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
      discardCurrentRecording();
      stopMediaTracks();
    };
  }, [discardCurrentRecording, stopMediaTracks]);

  return {
    isSupported,
    isBusy: status !== "idle",
    status,
    toggleRecording,
  };
}
