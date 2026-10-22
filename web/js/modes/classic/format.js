// Small text helpers for the classic mode UI.

export function templateText(template) {
  if (!template) return "？";
  return template.join(" ");
}

export function secondsLeft(deadlineAt, now) {
  if (deadlineAt == null) return 0;
  return Math.max(0, Math.ceil((deadlineAt - now) / 1000));
}

const REASONS = {
  time: "时间到",
  all_correct: "全部猜对",
  skipped: "已跳过",
  drawer_left: "画手离开了",
};

export function reasonText(reason) {
  return REASONS[reason] ?? "";
}
