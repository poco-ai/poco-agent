# Poco Frontend Design System

## Vision

Poco (Your Pocket Coworker) is designed to be a friendly, intelligent, and highly capable AI assistant. The design language balances "Editorial Refinement" with "Modern Utility".

## Core Principles

1. **Intelligent Simplicity**: Complex capabilities (MCP, Skills, Scheduling) should be easily accessible but not overwhelming.
2. **Editorial Refinement**: High-quality typography (Serif for headers) and generous spacing provide a professional, trustworthy feel.
3. **Fluidity & Feedback**: Every interaction should feel responsive and alive through purposeful animations and micro-interactions.

## Visual Language

### Typography

- **Brand/Headers**: `Libre Baskerville` (Serif). Used for high-level headings and brand identity.
- **Body/UI**: System Sans-serif stack. Focused on readability and platform familiarity.
- **Mono**: System Monospace. Used for code snippets and technical data.

### Color Palette (OKLCH)

- **Primary**: Teal/Green (`oklch(0.8348 0.1302 160.908)`). Symbolizes growth, intelligence, and calm.
- **Background**: Soft White (`oklch(0.9911 0 0)`) / Deep Charcoal (`oklch(0.1822 0 0)`).
- **Surface**: Subtle borders and light shadows to create depth without clutter.

### Backgrounds & Textures

- **Proposed**: Use subtle mesh gradients or noise textures to add depth and "atmosphere" to the application, moving away from solid fills.

## Component Patterns

### Task Composer

The central interaction point. Features:

- Integrated file attachments and repository cards.
- Mode toggling (Task, Plan, Scheduled).
- Contextual recommendations (MCP, Skills).
- Voice and Slash-command support.

### Hero Section

Designed to be engaging and interactive. The rotating text on hover highlights the versatility of Poco.

## Proposed Enhancements (Q2 2026)

### 1. Atmospheric Depth

Implement a dynamic, slow-moving mesh gradient in the background that reflects the `primary` color theme. This enhances the "AI as a living entity" feel.

### 2. Glassmorphism in UI

Introduce subtle `backdrop-blur` and translucent surfaces for floating components (Popovers, Dialogs, Composer) to create a sense of layering.

### 3. Enhanced Micro-interactions

- **Focus States**: Animated gradient borders for inputs.
- **Transitions**: Staggered entry animations for list items and cards.
- **Voice Feedback**: Visual waveform during transcription.

### 4. Distinctive Typography Pairing

Explore pairing `Libre Baskerville` with a more characterful sans-serif like `Plus Jakarta Sans` or `Outfit` for a more modern edge.
