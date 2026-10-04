import { z } from "zod";

/**
 * Camera Status enum matching backend CameraStatus.
 */
export const cameraStatusSchema = z.enum(["online", "offline", "unknown"]);
export type CameraStatus = z.infer<typeof cameraStatusSchema>;

/**
 * Schema validating API CameraRead responses.
 */
export const cameraReadSchema = z.object({
  id: z.number().int().positive(),
  camera_name: z.string(),
  location: z.string(),
  description: z.string(),
  ip_address: z.string(),
  status: cameraStatusSchema,
  consecutive_failures: z.number().int().nonnegative().default(0),
  last_checked: z.string().nullable(),
  last_online: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Camera = z.infer<typeof cameraReadSchema>;
export type CameraRead = Camera;

export const cameraListSchema = z.array(cameraReadSchema);

/**
 * Schema validating API MonitoringStatus responses.
 */
export const monitoringStatusSchema = z.object({
  running: z.boolean(),
  interval_seconds: z.number().int().positive(),
  running_since: z.string().nullable(),
  last_cycle_started_at: z.string().nullable(),
  last_cycle_finished_at: z.string().nullable(),
  next_check_at: z.string().nullable(),
  total: z.number().int().nonnegative(),
  online: z.number().int().nonnegative(),
  offline: z.number().int().nonnegative(),
  unknown: z.number().int().nonnegative(),
});
export type MonitoringStatus = z.infer<typeof monitoringStatusSchema>;

/**
 * Trim whitespace while preserving U+FEFF (BOM), matching Python str.strip()
 * where U+FEFF is not a whitespace character.
 * This ensures the frontend never accepts invalid inputs containing BOM that the backend rejects.
 */
export function trimWhitespace(val: string): string {
  return val.replace(
    /^[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g,
    ""
  );
}

/**
 * Helper to validate text fields: trim, check empty, reject control characters, and enforce max length.
 */
function createTextFieldSchema(maxLength: number) {
  return z
    .string()
    .transform((val) => trimWhitespace(val))
    .superRefine((val, ctx) => {
      if (!val) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "This field cannot be empty.",
        });
        return;
      }

      for (let i = 0; i < val.length; i++) {
        const code = val.charCodeAt(i);
        if (code < 32 || code === 127) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message:
              "Control characters including newlines and tabs are not allowed.",
          });
          return;
        }
      }

      if (val.length > maxLength) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Must be ${maxLength} characters or fewer.`,
        });
      }
    });
}

/**
 * Helper to validate IPv4 address strictly matching backend Pydantic rules and message strings.
 */
function createIpAddressSchema() {
  return z
    .string()
    .transform((val) => trimWhitespace(val))
    .superRefine((val, ctx) => {
      if (!val) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "This field cannot be empty.",
        });
        return;
      }

      const parts = val.split(".");
      if (parts.length === 4) {
        for (const part of parts) {
          if (part.length > 1 && part.startsWith("0")) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Leading zeros are not permitted in IP address octets.",
            });
            return;
          }
        }
      }

      // Strict dotted quad format with ASCII digits only
      const dottedQuadRegex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
      const match = val.match(dottedQuadRegex);
      if (!match) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Enter a valid IPv4 address such as 192.168.1.64.",
        });
        return;
      }

      const octets = [
        Number.parseInt(match[1], 10),
        Number.parseInt(match[2], 10),
        Number.parseInt(match[3], 10),
        Number.parseInt(match[4], 10),
      ];

      for (const octet of octets) {
        if (octet < 0 || octet > 255) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Enter a valid IPv4 address such as 192.168.1.64.",
          });
          return;
        }
      }

      if (
        octets[0] === 0 &&
        octets[1] === 0 &&
        octets[2] === 0 &&
        octets[3] === 0
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "0.0.0.0 is not a valid camera host address.",
        });
        return;
      }

      // Multicast range: 224.0.0.0 - 239.255.255.255
      if (octets[0] >= 224 && octets[0] <= 239) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message:
            "Multicast addresses (224.0.0.0/4) cannot be used as camera addresses.",
        });
        return;
      }

      if (
        octets[0] === 255 &&
        octets[1] === 255 &&
        octets[2] === 255 &&
        octets[3] === 255
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message:
            "255.255.255.255 is a broadcast address and cannot be used as a camera address.",
        });
      }
    });
}

/**
 * Camera form input validation schema.
 */
export const cameraFormSchema = z.object({
  camera_name: createTextFieldSchema(100),
  location: createTextFieldSchema(100),
  description: createTextFieldSchema(500),
  ip_address: createIpAddressSchema(),
});
export type CameraFormData = z.infer<typeof cameraFormSchema>;

/**
 * Server error schemas supporting string or numeric loc paths and optional total_errors.
 */
export const apiErrorDetailItemSchema = z.object({
  loc: z.array(z.union([z.string(), z.number()])),
  msg: z.string(),
  type: z.string(),
});
export type ApiErrorDetailItem = z.infer<typeof apiErrorDetailItemSchema>;

export const apiErrorResponseSchema = z.object({
  detail: z.union([z.string(), z.array(apiErrorDetailItemSchema)]),
  total_errors: z.number().int().optional(),
});
export type ApiErrorResponse = z.infer<typeof apiErrorResponseSchema>;

/**
 * CSV Import response schemas.
 */
export const cameraImportPreviewSchema = z.object({
  count: z.number().int().nonnegative(),
  preview: z.array(
    z.object({
      camera_name: z.string(),
      location: z.string(),
      description: z.string(),
      ip_address: z.string(),
    })
  ),
});
export type CameraImportPreview = z.infer<typeof cameraImportPreviewSchema>;

export const cameraImportSuccessSchema = z.object({
  imported: z.number().int().nonnegative(),
});
export type CameraImportSuccess = z.infer<typeof cameraImportSuccessSchema>;
