import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const customTwMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["page-title", "section-heading", "table"] }],
      rounded: [{ rounded: ["control", "dialog"] }],
      "max-w": [{ "max-w": ["page"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return customTwMerge(clsx(inputs));
}
