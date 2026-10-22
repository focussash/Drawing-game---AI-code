// localStorage that never throws: private mode, blocked storage and old
// browsers all fall back to "nothing saved" instead of breaking the page.

export const keys = {
  nickname: "nhwc.nickname",
  token: (code) => `nhwc.token.${code}`,
  wechatHintDismissed: "nhwc.wechat-hint-dismissed",
};

function defaultStore() {
  try {
    return globalThis.localStorage;
  } catch {
    return undefined;
  }
}

export function safeGet(key, fallback = null, store = defaultStore()) {
  try {
    const value = store?.getItem(key);
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

export function safeSet(key, value, store = defaultStore()) {
  try {
    if (!store) return false;
    store.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}
