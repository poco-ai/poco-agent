/**
 * Sound utility using Web Audio API
 * Generates simple tones without requiring audio files
 */

// Create a shared audio context
let audioContext: AudioContext | null = null;

const getAudioContext = (): AudioContext => {
  if (!audioContext) {
    const AudioContextClass =
      window.AudioContext ||
      (window as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (AudioContextClass) {
      audioContext = new AudioContextClass();
    } else {
      throw new Error("AudioContext is not supported");
    }
  }
  return audioContext;
};

/**
 * Play a simple tone
 * @param frequency - Frequency of the tone in Hz
 * @param duration - Duration of the tone in milliseconds
 * @param type - Type of oscillator wave
 */
const playTone = (
  frequency: number,
  duration: number,
  type: OscillatorType = "sine",
): void => {
  try {
    const ctx = getAudioContext();
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = type;

    // Envelope for smooth sound
    const now = ctx.currentTime;
    gainNode.gain.setValueAtTime(0, now);
    gainNode.gain.linearRampToValueAtTime(0.3, now + 0.01); // Attack
    gainNode.gain.exponentialRampToValueAtTime(0.01, now + duration / 1000); // Decay

    oscillator.start(now);
    oscillator.stop(now + duration / 1000);
  } catch (error) {
    console.warn("Failed to play sound:", error);
  }
};

/**
 * Play a sequence of tones
 */
const playSequence = (
  notes: Array<{ frequency: number; duration: number; delay: number }>,
): void => {
  notes.forEach(({ frequency, duration, delay }) => {
    setTimeout(() => playTone(frequency, duration), delay);
  });
};

/**
 * Task completion sound - ascending two-tone chime
 */
export const playTaskCompleteSound = (): void => {
  playSequence([
    { frequency: 523.25, duration: 120, delay: 0 }, // C5
    { frequency: 659.25, duration: 150, delay: 100 }, // E5
  ]);
};

/**
 * File upload success sound - quick rising beep
 */
export const playFileUploadSound = (): void => {
  playSequence([
    { frequency: 440, duration: 80, delay: 0 }, // A4
    { frequency: 554.37, duration: 80, delay: 70 }, // C#5
    { frequency: 659.25, duration: 120, delay: 140 }, // E5
  ]);
};

/**
 * MCP skill installation sound - confirmation beep
 */
export const playMcpInstallSound = (): void => {
  playSequence([
    { frequency: 659.25, duration: 100, delay: 0 }, // E5
    { frequency: 523.25, duration: 100, delay: 90 }, // C5
    { frequency: 659.25, duration: 150, delay: 180 }, // E5
  ]);
};
