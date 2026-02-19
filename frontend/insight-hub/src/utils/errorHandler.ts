/**
 * Extract readable error message from various error types
 */
export function extractErrorMessage(err: any): string {
  // Check for backend error response with detail
  if (err?.response?.data?.detail) {
    return err.response.data.detail;
  }

  // Check for backend error response with message
  if (err?.response?.data?.message) {
    return err.response.data.message;
  }

  // Check for Error object with message
  if (err instanceof Error) {
    return err.message;
  }

  // Check for string error
  if (typeof err === "string") {
    return err;
  }

  // Check for generic object with message
  if (err?.message && typeof err.message === "string") {
    return err.message;
  }

  // Default fallback
  return "Something went wrong. Please try again.";
}
