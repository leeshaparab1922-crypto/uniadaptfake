import { createSlice, nanoid, type PayloadAction } from "@reduxjs/toolkit";

export type NotificationKind = "success" | "error";

export interface Notification {
  id: string;
  kind: NotificationKind;
  message: string;
}

/** Client-only UI state: transient toast notifications for admin mutations. */
const notificationsSlice = createSlice({
  name: "notifications",
  initialState: [] as Notification[],
  reducers: {
    pushNotification: {
      reducer: (state, action: PayloadAction<Notification>) => {
        state.push(action.payload);
      },
      prepare: (kind: NotificationKind, message: string) => ({
        payload: { id: nanoid(), kind, message },
      }),
    },
    dismissNotification: (state, action: PayloadAction<string>) =>
      state.filter((n) => n.id !== action.payload),
  },
});

export const { pushNotification, dismissNotification } = notificationsSlice.actions;
export default notificationsSlice.reducer;
