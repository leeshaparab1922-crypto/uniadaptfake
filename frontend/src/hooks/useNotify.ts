import { useMemo } from "react";
import { useDispatch } from "react-redux";

import { pushNotification } from "../store/notificationsSlice";

/** Dispatches toast notifications; `error` accepts any thrown value and
 * surfaces the backend `detail` message carried by `ApiError`. */
export function useNotify() {
  const dispatch = useDispatch();
  return useMemo(
    () => ({
      success: (message: string) => dispatch(pushNotification("success", message)),
      error: (err: unknown) =>
        dispatch(
          pushNotification("error", err instanceof Error ? err.message : "Something went wrong"),
        ),
    }),
    [dispatch],
  );
}
