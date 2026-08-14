import type { Role } from "@distresslens/contracts";

/** The one Vietnamese label per role, shared by the account menu and the demo-profile switcher. */
export const ROLE_LABELS: Record<Role, string> = {
  analyst: "Chuyên viên phân tích",
  platform_viewer: "Nền tảng — chỉ đọc",
  platform_operator: "Nền tảng — vận hành",
  platform_admin: "Quản trị viên",
};
