import { test } from "node:test";
import assert from "node:assert/strict";
import { isWeChat } from "../../web/js/ui/banner.js";

test("detects the WeChat in-app browser", () => {
  const wechat = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003129) NetType/WIFI Language/zh_CN";
  const safari = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
  assert.equal(isWeChat(wechat), true);
  assert.equal(isWeChat(safari), false);
  assert.equal(isWeChat(undefined), false);
});
