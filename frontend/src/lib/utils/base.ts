import type { HTTPValidationError } from "@/openapi";

export function handleApi<T>(
  response:
    | { status: 200; data: T; headers: Headers }
    | { status: number; data: HTTPValidationError; headers: Headers },
): T {
  console.log(response);
  if (response.status === 200) {
    return response.data as T;
  }
  throw response.data;
}
