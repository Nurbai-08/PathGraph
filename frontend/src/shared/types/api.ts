export type ApiErrorDetail = {
  code: string;
  message: string;
};

export type ApiResponse<T> = {
  data: T | null;
  error: ApiErrorDetail | null;
};

