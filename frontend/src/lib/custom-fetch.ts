const getBody = <T>(c: Response | Request): Promise<T> => {
  const contentType = c.headers.get("content-type");

  if (contentType && contentType.includes("application/json")) {
    return c.json();
  }

  if (contentType && contentType.includes("application/pdf")) {
    return c.blob() as Promise<T>;
  }

  return c.text() as Promise<T>;
};

const getUrl = (contextUrl: string): string => {
  const baseUrl = import.meta.env.VITE_HTTP_BASE_URL;
  const url = new URL(baseUrl + contextUrl);
  const pathname = url.pathname;
  const search = url.search;

  const requestUrl = new URL(`${baseUrl}${pathname}${search}`);

  return requestUrl.toString();
};

const getHeaders = (headers?: HeadersInit): HeadersInit => {
  const normalizedHeaders: Record<string, string> = headers
    ? { ...(headers as Record<string, string>) }
    : {};

  // const token = getToken();

  // if (token && !normalizedHeaders["Authorization"]) {
  //   normalizedHeaders["Authorization"] = `Bearer ${token}`;
  // }

  return normalizedHeaders;
};

export const customFetch = async <T>(
  url: string,
  options: RequestInit,
): Promise<T> => {
  const requestUrl = getUrl(url);

  const requestHeaders = getHeaders(options.headers);

  const requestInit: RequestInit = {
    ...options,
    headers: requestHeaders,
    credentials: "include",
  };

  const rsp = await fetch(requestUrl, requestInit);
  if (!rsp.ok) {
    const errorText = await rsp.json();
    throw { status: rsp.status, error: errorText };
  }
  const data = await getBody<T>(rsp);

  return { status: rsp.status, data, headers: rsp.headers } as T;
};
