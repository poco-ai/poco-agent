import { apiClient, API_ENDPOINTS } from "../../../services/api-client.ts";

export interface AudioTranscriptionResult {
  text: string;
}

interface TranscribeAudioOptions {
  language?: string;
  signal?: AbortSignal;
}

export async function transcribeAudio(
  file: File,
  options: TranscribeAudioOptions = {},
): Promise<AudioTranscriptionResult> {
  const formData = new FormData();
  formData.append("file", file);

  const language = (options.language || "").trim().toLowerCase();
  if (language) {
    formData.append("language", language);
  }

  return apiClient.post<AudioTranscriptionResult>(
    API_ENDPOINTS.audioTranscriptions,
    formData,
    {
      signal: options.signal,
      timeoutMs: 180_000,
    },
  );
}
