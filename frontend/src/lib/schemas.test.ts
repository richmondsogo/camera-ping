import { describe, it, expect } from "vitest";
import { cameraFormSchema } from "./schemas";
import vectors from "../../../shared/camera-validation-vectors.json";

describe("Camera Validation Parity with Shared Vectors", () => {
  for (const vector of vectors) {
    const {
      field,
      input,
      expected,
      expected_stored,
      expected_message,
      frontend_stricter,
    } = vector;

    it(`validates ${field} with input ${JSON.stringify(input)}`, () => {
      const fieldSchema =
        cameraFormSchema.shape[field as keyof typeof cameraFormSchema.shape];
      const result = fieldSchema.safeParse(input);

      if (frontend_stricter) {
        expect(result.success).toBe(false);
        return;
      }

      if (expected === "valid") {
        expect(result.success).toBe(true);
        if (result.success && expected_stored !== null) {
          expect(result.data).toBe(expected_stored);
        }
      } else {
        expect(result.success).toBe(false);
        if (!result.success && expected_message) {
          const messages = result.error.issues.map((i) => i.message);
          expect(messages).toContain(expected_message);
        }
      }
    });
  }
});
