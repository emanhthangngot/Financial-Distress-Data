import type { UiState } from "@distresslens/contracts";
import type { RequestContext } from "@/lib/data/port";
import { ButtonLink } from "./button";

/**
 * The action rendered next to a `StatePanel`'s denial copy.
 *
 * A guest is not forbidden, they are anonymous, so their action is "sign in"
 * rather than "reload" -- reloading changes nothing for someone who was never
 * signed in. `ROUTE_FORBIDDEN_GUEST_COPY` already gives the copy the same
 * framing; this is the matching call to action.
 */
export function DenialAction({
  state,
  context,
  reloadHref,
}: {
  state: UiState;
  context: RequestContext;
  /** Where the ordinary (non-guest) denial's "Tải lại" link points. */
  reloadHref: string;
}) {
  if (state === "forbidden" && context.userId === null) {
    return (
      <ButtonLink href="/sign-in" variant="primary">
        Đăng nhập
      </ButtonLink>
    );
  }

  return (
    <ButtonLink href={reloadHref} variant="secondary">
      Tải lại
    </ButtonLink>
  );
}
