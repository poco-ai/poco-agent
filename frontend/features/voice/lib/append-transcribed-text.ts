export function appendTranscribedText(
  currentValue: string,
  transcription: string,
): string {
  const trimmedTranscription = transcription.trim();
  if (!trimmedTranscription) {
    return currentValue;
  }

  if (!currentValue.trim()) {
    return trimmedTranscription;
  }

  const separator = /\s$/.test(currentValue) ? "" : " ";
  return `${currentValue}${separator}${trimmedTranscription}`;
}
