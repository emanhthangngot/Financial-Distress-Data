import type { StateCopy, UiState } from "@distresslens/contracts";

/**
 * The route/state inventory from phase-02, with the copy each non-success state
 * renders. Keeping the copy here rather than inline in components is what makes
 * "every state explains the safe next action" checkable: a test walks this
 * catalog, and a route that invents an unlisted state fails to typecheck.
 */

export const PRODUCT_ROUTES = [
  "/",
  "/companies",
  "/companies/[ticker]",
  "/compare",
  "/reports",
  "/reports/[id]",
  "/agents/registry",
  "/ops/evidence",
] as const;

export type ProductRoute = (typeof PRODUCT_ROUTES)[number];

type NonSuccessState = Exclude<UiState, "success" | "loading">;

export type RouteStateCatalog = Record<ProductRoute, Partial<Record<NonSuccessState, StateCopy>>>;

export const ROUTE_STATE_COPY: RouteStateCatalog = {
  "/": {
    // The signed-out case for `/` is a landing page, not an error screen: the
    // copy invites sign-in rather than reporting a failure.
    forbidden: {
      unavailable: "Bạn chưa đăng nhập nên chưa xem được danh mục rủi ro.",
      lastKnown: null,
      nextAction: "Đăng nhập bằng tài khoản được cấp để xem tổng quan danh mục.",
    },
    error: {
      unavailable: "Không xác thực được phiên đăng nhập.",
      lastKnown: null,
      nextAction: "Đăng nhập lại. Nếu vẫn lỗi, liên hệ quản trị viên hệ thống.",
    },
    degraded: {
      unavailable: "Một phần dữ liệu tổng quan chưa cập nhật.",
      lastKnown: "Đang hiển thị số liệu của lần đồng bộ gần nhất.",
      nextAction: "Xem mốc thời gian dữ liệu trên tiêu đề trước khi ra quyết định.",
    },
  },
  "/companies": {
    forbidden: {
      unavailable: "Tài khoản hiện tại không được phép tra cứu doanh nghiệp.",
      lastKnown: null,
      nextAction: "Đăng nhập bằng tài khoản phân tích, hoặc yêu cầu cấp quyền analyst.",
    },
    empty: {
      unavailable: "Không có doanh nghiệp nào khớp từ khóa.",
      lastKnown: null,
      nextAction: "Thử mã chứng khoán (ví dụ: HPG) hoặc bỏ bớt bộ lọc.",
    },
    stale: {
      unavailable: "Dữ liệu xếp hạng chưa chạy trong kỳ mới nhất.",
      lastKnown: "Đang hiển thị kết quả của kỳ dữ liệu trước.",
      nextAction: "Đối chiếu cột “Dữ liệu đến” trước khi so sánh giữa các doanh nghiệp.",
    },
    error: {
      unavailable: "Không gọi được dịch vụ tìm kiếm doanh nghiệp.",
      lastKnown: null,
      nextAction: "Tải lại trang. Danh sách theo dõi đã lưu vẫn truy cập được.",
    },
  },
  "/companies/[ticker]": {
    degraded: {
      unavailable: "Suy luận trực tuyến đang không khả dụng (EKS ngoại tuyến).",
      lastKnown: "Đang hiển thị kết quả đã lưu, có mốc thời gian và phiên bản mô hình.",
      nextAction: "Đọc kết quả đã lưu, hoặc chờ phiên evidence được tạo lại.",
    },
    empty: {
      unavailable: "Chưa có kết quả chấm điểm cho doanh nghiệp này.",
      lastKnown: null,
      nextAction: "Kiểm tra lại mã doanh nghiệp hoặc chọn từ danh sách Doanh nghiệp.",
    },
    forbidden: {
      unavailable: "Tài khoản hiện tại không được cấp quyền xem doanh nghiệp này.",
      lastKnown: null,
      nextAction: "Yêu cầu quản trị viên cấp quyền, hoặc quay lại danh mục được phép.",
    },
    error: {
      unavailable: "Không tải được hồ sơ rủi ro của doanh nghiệp.",
      lastKnown: null,
      nextAction: "Tải lại trang hoặc mở báo cáo đã lưu gần nhất.",
    },
  },
  "/compare": {
    forbidden: {
      unavailable: "Tài khoản hiện tại không được phép so sánh phiên bản mô hình.",
      lastKnown: null,
      nextAction: "Đăng nhập bằng tài khoản phân tích, hoặc yêu cầu cấp quyền analyst.",
    },
    empty: {
      unavailable: "Chưa có phiên bản mô hình nền để so sánh.",
      lastKnown: "Đang hiển thị kết quả của phiên bản ứng viên.",
      nextAction: "Chọn một phiên bản nền khác, hoặc chờ mô hình kế tiếp được promote.",
    },
    error: {
      unavailable: "Không tải được kết quả so sánh hai phiên bản.",
      lastKnown: null,
      nextAction: "Tải lại trang. Trang chi tiết doanh nghiệp vẫn xem được.",
    },
  },
  "/reports": {
    forbidden: {
      unavailable: "Tài khoản hiện tại không được phép xem báo cáo đã lưu.",
      lastKnown: null,
      nextAction: "Đăng nhập bằng tài khoản phân tích, hoặc yêu cầu cấp quyền analyst.",
    },
    empty: {
      unavailable: "Bạn chưa lưu báo cáo nào.",
      lastKnown: null,
      nextAction: "Mở một doanh nghiệp và chọn “Lưu báo cáo” để tạo báo cáo đầu tiên.",
    },
    error: {
      unavailable: "Không tải được danh sách báo cáo đã lưu.",
      lastKnown: null,
      nextAction: "Tải lại trang. Trang chi tiết doanh nghiệp vẫn xem được.",
    },
  },
  "/reports/[id]": {
    forbidden: {
      unavailable: "Báo cáo đã bị thu hồi hoặc không thuộc tài khoản này.",
      lastKnown: null,
      nextAction: "Quay lại danh sách Báo cáo để mở báo cáo bạn sở hữu.",
    },
    error: {
      unavailable: "Không mở được báo cáo đã lưu.",
      lastKnown: null,
      nextAction: "Tải lại trang, hoặc tạo lại báo cáo từ trang doanh nghiệp.",
    },
  },
  "/agents/registry": {
    forbidden: {
      unavailable: "Chỉ vai trò nền tảng mới xem được sổ đăng ký agent.",
      lastKnown: null,
      nextAction: "Yêu cầu cấp vai trò nền tảng, hoặc quay lại khu vực phân tích.",
    },
    degraded: {
      unavailable: "Không đọc được số bản sao đang chạy (EKS ngoại tuyến).",
      lastKnown: "Đang hiển thị phiên bản và chính sách sandbox đã đăng ký.",
      nextAction: "Tạo phiên evidence để đọc lại tình trạng bản sao.",
    },
    error: {
      unavailable: "Không tải được sổ đăng ký agent.",
      lastKnown: null,
      nextAction: "Tải lại trang, hoặc kiểm tra trạng thái Supabase ở trang Vận hành.",
    },
  },
  "/ops/evidence": {
    forbidden: {
      unavailable: "Tài khoản hiện tại không có quyền vào trung tâm vận hành.",
      lastKnown: null,
      nextAction: "Yêu cầu vai trò platform_viewer trở lên từ quản trị viên.",
    },
    degraded: {
      unavailable: "Mặt phẳng evidence đang ngoại tuyến, không đọc được trạng thái Argo trực tiếp.",
      lastKnown: "Đang hiển thị revision và chi phí ghi nhận ở lần đồng bộ cuối.",
      nextAction: "Tạo phiên evidence mới, hoặc xem lịch sử audit để biết lần chạy gần nhất.",
    },
    error: {
      unavailable: "Không tải được bảng điều khiển vận hành.",
      lastKnown: null,
      nextAction: "Tải lại trang. Thao tác hủy phiên vẫn khả dụng khi trang tải lại được.",
    },
  },
};

/**
 * Guest-specific override of a route's "forbidden" copy.
 *
 * A signed-out visitor is not forbidden, they are anonymous -- denying them
 * with the same "not permitted" copy shown to a signed-in user with the wrong
 * role reads as a permanent wall instead of an invitation to sign in. Only
 * routes that a guest can reach at all need an entry here: `/` already writes
 * guest-oriented copy directly into its `forbidden` state (a guest is the only
 * caller `/` ever denies), so it has no override.
 */
export const ROUTE_FORBIDDEN_GUEST_COPY: Partial<Record<ProductRoute, StateCopy>> = {
  "/companies": {
    unavailable: "Đăng nhập để tra cứu doanh nghiệp.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản phân tích để xem danh mục rủi ro.",
  },
  "/companies/[ticker]": {
    unavailable: "Đăng nhập để xem hồ sơ rủi ro của doanh nghiệp này.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản phân tích để xem chi tiết.",
  },
  "/compare": {
    unavailable: "Đăng nhập để so sánh phiên bản mô hình.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản phân tích để xem so sánh.",
  },
  "/reports": {
    unavailable: "Đăng nhập để xem báo cáo đã lưu.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản phân tích để xem báo cáo của bạn.",
  },
  "/reports/[id]": {
    unavailable: "Đăng nhập để mở báo cáo này.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản phân tích để tiếp tục.",
  },
  "/agents/registry": {
    unavailable: "Đăng nhập để xem sổ đăng ký agent.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản vai trò nền tảng để tiếp tục.",
  },
  "/ops/evidence": {
    unavailable: "Đăng nhập để vào trung tâm vận hành.",
    lastKnown: null,
    nextAction: "Đăng nhập bằng tài khoản vai trò nền tảng để tiếp tục.",
  },
};

/**
 * The analysis assistant is a floating surface available on every route rather
 * than a destination of its own, so its states live outside the route catalog.
 * It still owes the reader the same three answers as any route state.
 */
export const ASSISTANT_STATE_COPY: Partial<Record<NonSuccessState, StateCopy>> = {
  forbidden: {
    unavailable: "Tài khoản hiện tại không được phép gửi yêu cầu tới trợ lý phân tích.",
    lastKnown: null,
    nextAction: "Yêu cầu cấp quyền analyst, hoặc xem phân tích đã lưu trong Báo cáo.",
  },
  degraded: {
    unavailable: "Trợ lý không chạy được vì phiên evidence chưa ở trạng thái READY.",
    lastKnown: "Đang hiển thị các câu trả lời đã lưu của phiên trước.",
    nextAction: "Đọc lại phân tích đã lưu, hoặc đề nghị vận hành tạo phiên evidence.",
  },
  timeout: {
    unavailable: "Trợ lý không trả lời trong thời gian cho phép.",
    lastKnown: "Phần trả lời đã nhận được vẫn giữ nguyên bên dưới.",
    nextAction: "Hỏi lại với phạm vi hẹp hơn, hoặc thử lại sau ít phút.",
  },
  policy_blocked: {
    unavailable: "Yêu cầu bị chính sách an toàn chặn.",
    lastKnown: null,
    nextAction: "Đặt lại câu hỏi ở phạm vi phân tích tài chính của doanh nghiệp.",
  },
  error: {
    unavailable: "Không gửi được yêu cầu tới trợ lý phân tích.",
    lastKnown: null,
    nextAction: "Thử lại. Nếu lặp lại, xem trạng thái hệ thống ở trang Vận hành.",
  },
};
