import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const customTwMerge = extendTailwindMerge({
  extend: {
    theme: {
      spacing: [
        "header",
        "gutter",
        "section",
        "container-bottom",
        "stack",
        "dialog-pad",
        "toolbar",
        "button-x",
        "cell-x",
        "row-header",
        "row-body",
        "control-x",
        "inline",
        "tight",
        "popup-pad",
        "item-gap",
        "panel-pad",
        "trigger-status",
        "trigger-location",
        "select-indicator",
        "popup-max",
      ],
    },
    classGroups: {
      "font-size": [{ text: ["page-title", "section-heading", "table"] }],
      rounded: [{ rounded: ["control", "dialog"] }],
      "max-w": [{ "max-w": ["page"] }],
      w: ["w-dialog"],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return customTwMerge(clsx(inputs));
}
