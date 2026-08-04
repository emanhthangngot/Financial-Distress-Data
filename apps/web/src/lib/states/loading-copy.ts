import type { StateCopy } from "@distresslens/contracts";

/**
 * Loading copy per surface.
 *
 * `loading` is the one state the route catalog does not carry, because it is
 * not a failure and never needs a recovery action from the server. It still
 * needs words: a surface that renders nothing while it waits is
 * indistinguishable from one that failed silently.
 */
export const LOADING_COPY: Record<string, StateCopy> = {
  overview: {
    unavailable: "Đang tải số liệu tổng quan danh mục.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, tải lại.",
  },
  companies: {
    unavailable: "Đang tải danh sách doanh nghiệp.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, tải lại.",
  },
  companyDetail: {
    unavailable: "Đang tải hồ sơ rủi ro của doanh nghiệp.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, mở lại từ danh sách Doanh nghiệp.",
  },
  compare: {
    unavailable: "Đang tải kết quả so sánh hai phiên bản mô hình.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, tải lại.",
  },
  report: {
    unavailable: "Đang tải báo cáo đã lưu.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, quay lại danh sách Báo cáo.",
  },
  registry: {
    unavailable: "Đang tải sổ đăng ký agent.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, tải lại.",
  },
  ops: {
    unavailable: "Đang tải bảng điều khiển vận hành.",
    lastKnown: null,
    nextAction: "Chờ vài giây. Nếu trang không tải xong, tải lại.",
  },
};
