import type { Provider } from "./types";

export interface ProviderMeta {
  id: Provider;
  label: string;
  /** Tailwind text-color class for the provider dot. */
  dot: string;
  /** Tailwind classes for a subtle tinted badge. */
  tint: string;
}

/**
 * Provider identity for tasteful, trademark-safe visual distinction (colored
 * dots/badges only — no official logos, no model IDs).
 */
export const PROVIDERS: Record<Provider, ProviderMeta> = {
  openai: {
    id: "openai",
    label: "OpenAI",
    dot: "text-openai",
    tint: "bg-openai/10 text-openai",
  },
  anthropic: {
    id: "anthropic",
    label: "Anthropic",
    dot: "text-anthropic",
    tint: "bg-anthropic/10 text-anthropic",
  },
  gemini: {
    id: "gemini",
    label: "Gemini",
    dot: "text-gemini",
    tint: "bg-gemini/10 text-gemini",
  },
};

export const PROVIDER_ORDER: Provider[] = ["openai", "anthropic", "gemini"];
