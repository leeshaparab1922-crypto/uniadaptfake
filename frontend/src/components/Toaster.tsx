import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";

import { dismissNotification, type Notification } from "../store/notificationsSlice";
import type { RootState } from "../store";

const AUTO_DISMISS_MS = 6000;

function Toast({ notification }: { notification: Notification }) {
  const dispatch = useDispatch();
  useEffect(() => {
    const timer = setTimeout(() => dispatch(dismissNotification(notification.id)), AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [dispatch, notification.id]);

  const colour = notification.kind === "success" ? "bg-green-600" : "bg-red-600";
  return (
    <div
      role={notification.kind === "error" ? "alert" : "status"}
      data-testid={`toast-${notification.kind}`}
      className={`flex items-start gap-3 rounded px-4 py-2 text-sm text-white shadow ${colour}`}
    >
      <span className="flex-1">{notification.message}</span>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => dispatch(dismissNotification(notification.id))}
      >
        x
      </button>
    </div>
  );
}

/** Fixed-position stack of toast notifications; mount once under the Provider. */
export default function Toaster() {
  const notifications = useSelector((state: RootState) => state.notifications);
  return (
    <div className="fixed right-4 top-4 z-50 flex max-w-sm flex-col gap-2" data-testid="toaster">
      {notifications.map((n) => (
        <Toast key={n.id} notification={n} />
      ))}
    </div>
  );
}
