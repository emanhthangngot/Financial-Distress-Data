You are a Senior Product Designer and Senior Frontend Engineer specializing in enterprise financial dashboards and AI-powered SaaS products.

Your task is to inspect the entire DistressLens codebase, evaluate its current UI/UX, and improve the interface according to the following design direction:

- 80% Enterprise Fintech
- 20% AI-first
- The platform must feel professional, trustworthy, analytical, and suitable for financial analysts.
- AI must act as a supporting analysis assistant rather than dominating the interface.
- Do not turn the product into a chatbot-centric experience or a visually excessive AI application.
- Do not change business logic, API contracts, or existing data flows unless it is genuinely necessary.

## 1. Start by inspecting and understanding the codebase

Before modifying any code, inspect:

- The project directory structure.
- The framework and framework version.
- package.json or equivalent dependency files.
- Routing architecture.
- Global layout structure.
- Sidebar, header, dashboard, and shared components.
- The current styling system, such as Tailwind CSS, CSS Modules, styled-components, SCSS, or a UI component library.
- Existing design tokens.
- State management.
- API calls, mock data, loading states, and error states.
- Role-based permissions.
- Responsive behavior.
- Charting libraries.
- Icon libraries.
- Current typography and font setup.

Do not rewrite the entire project from scratch.

Reuse existing components whenever reasonable and follow the project’s established coding conventions.

After inspecting the codebase, provide a concise summary containing:

1. The current frontend architecture.
2. The files and components directly related to the dashboard.
3. The main UI/UX problems.
4. The proposed improvements.
5. Potential risks that may affect existing functionality.

Only begin implementation after understanding the current structure.

---

## 2. Overall design direction

Redesign the product using a Modern Enterprise Fintech visual language.

The interface should be:

- Professional.
- Minimal.
- Trustworthy.
- Data-focused.
- Easy to scan.
- Clear in its information hierarchy.
- Suitable for financial analysis.
- Modern without being overly decorative.

The intended product feeling is:

Trustworthy → Analytical → Transparent → Modern.

Avoid designing the application like:

- A marketing landing page.
- A full-screen chatbot.
- A neon crypto dashboard.
- A generic admin template.
- An interface with excessive gradients, shadows, glowing effects, or glassmorphism.

AI may have a subtle visual identity, but it must remain integrated into the financial product rather than becoming the main visual focus.

---

## 3. Design system recommendations

Create or standardize design tokens while integrating them with the existing styling system.

### Suggested colors

- Application background: `#F6F8FB`
- Surface and cards: `#FFFFFF`
- Sidebar navy: `#172A46`
- Primary blue: `#2563EB`
- AI accent: `#6366F1`
- Success: `#15966A`
- Warning: `#D97706`
- Critical: `#DC4545`
- Primary text: `#172033`
- Secondary text: `#64748B`
- Borders: `#E5EAF0`
- Hover surface: `#F1F5F9`

Use semantic colors consistently.

Do not communicate status using color alone. Include labels, icons, shapes, or text where appropriate.

### Shape and spacing

- Card border radius: `12px`
- Button border radius: `8–10px`
- Input border radius: `8–10px`
- Card padding: `20–24px`
- Grid gap: `16–24px`
- Border width: `1px`
- Shadows: subtle and used only to separate interface layers

### Typography

- Page title: `28–32px`, semibold
- Section title: `18–20px`, semibold
- KPI value: `28–36px`, bold
- Body text: `14–16px`
- Metadata: `12–13px`
- Commit hashes and technical identifiers: monospace

Keep the current font if it is appropriate. Do not add another font unless there is a clear reason.

---

## 4. Improve the application shell

### Sidebar

Modernize the existing sidebar:

- Use a width of approximately `220–232px`.
- Support collapsing if the current architecture allows it.
- Do not use an oversized solid white rectangle for the active item.
- Use a subtle light-blue or semi-transparent active background.
- Change the active icon and text to the primary color.
- Add a small active indicator along the left edge.
- Keep menu-item spacing consistent.
- Organize navigation into logical groups, such as:
  - Analysis
  - Management
  - System
- Add tooltips explaining unavailable features.
- Use a “Coming soon” badge when a feature has not been implemented instead of showing only a lock icon.
- Keep Settings and Sign out at the bottom.

### Header

Simplify the header:

- Search should remain the primary element.
- Show a concise data synchronization status.
- Include notifications.
- Include the user avatar and account menu.
- Avoid displaying excessive technical metadata directly.

Reduce the technical status row to something similar to:

“Data synchronized · Model v2.1 · View system details”

Move the following information into a popover, drawer, modal, or dedicated system-details page:

- Fixture name.
- Source hash.
- GitOps commit.
- Agent ID.
- Pipeline version.
- Internal environment metadata.

---

## 5. Redesign the Overview dashboard

The Overview page must no longer contain a large, meaningless empty area.

### Page header

Include:

- The title “Portfolio Overview”.
- A concise description.
- The most recent update timestamp.
- A time-range filter.
- An appropriate primary action such as “Generate report” or “Export report”.

Remove the existing “Analyze with AI” button from the page header.

### Disclaimer

Transform the current disclaimer into a compact information banner.

Example:

“This platform is intended for research and internal risk assessment. It does not provide investment advice.”

The banner should include:

- An information icon.
- A subtle blue-gray background.
- Concise text.
- An optional dismiss action when appropriate.

It should not occupy excessive vertical space.

### KPI cards

Create a four-card KPI section using real application data where available.

Suggested metrics:

1. Companies monitored.
2. High-risk companies.
3. New alerts.
4. Portfolio health score.

Each KPI card should include:

- A clear label.
- The primary value.
- A comparison with the previous period.
- An upward or downward trend.
- A tooltip explaining the metric.
- A drill-down interaction when a corresponding route already exists.

Do not inject fake data into the production data flow.

When data is unavailable, use an appropriate loading, unavailable, or empty state.

### Analytics section

Create a responsive analytics grid.

Suggested layout:

- Left side: risk trend over time.
- Right side: company distribution by risk level.

Risk categories may include:

- Low.
- Medium.
- High.
- Critical.

Charts must include:

- Clear legends.
- Tooltips.
- Empty states.
- Loading skeletons.
- Responsive behavior.
- A restrained color palette.
- Proper labels and accessible descriptions.

### Priority companies

Add a “Companies requiring attention” section.

Display information such as:

- Company symbol.
- Company name.
- Risk score.
- Risk category.
- Recent score movement.
- Main risk signal.
- Last update.
- Action to view details.

Use either a compact table or structured list based on the existing application patterns.

### Recent activity

Add a recent activity section when supported by the current backend.

Possible activities include:

- A new risk alert was detected.
- A company’s risk score changed.
- A report was generated.
- Company data was updated.
- A model analysis was completed.

Do not invent production activities when the backend does not provide them.

When recent-activity data is unavailable, show a meaningful empty state or omit the section.

---

## 6. Floating AI analysis assistant

Remove or replace the existing “Analyze with AI” button in the top-right area.

The AI functionality must become a floating assistant fixed to the bottom-right corner of the screen.

### Floating AI button

Create a floating action button with the following behavior:

- `position: fixed`
- Approximately `24px` from the bottom.
- Approximately `24px` from the right.
- Approximately `52–58px` in size.
- A sufficiently high z-index, while remaining below modals and critical overlays.
- A recognizable AI assistant icon.
- Primary blue or AI accent color.
- Only a very subtle gradient when needed.
- A moderate shadow to distinguish it from the page.
- Hover, focus, active, and disabled states.
- Tooltip: “AI Analysis Assistant”.
- Accessible `aria-label`.
- Full keyboard support.
- It must not cover important controls or page content.

Use restrained motion:

- A small hover scale effect.
- Transitions around `150–200ms`.
- No continuous pulsing.
- No intense glowing effects.
- No distracting animation.

The button may display a small badge when there is a relevant AI-generated insight or unfinished response, but avoid unnecessary notification noise.

### Desktop AI panel

When the floating button is clicked, open a panel on the right side.

Recommended behavior:

- Width of approximately `380–420px`.
- Height constrained to the viewport.
- Some spacing from the screen edges.
- Subtle border and shadow.
- Clear header.
- Minimize and close controls.
- It must not cover the entire dashboard.
- It should not permanently resize the main layout unless the existing application architecture supports that behavior well.
- Use a drawer, floating panel, or popover-based workspace depending on the existing component system.

Suggested panel header:

- AI icon.
- Title: “Analysis Assistant”.
- Ready, processing, or unavailable status.
- Minimize button.
- Close button.

The initial state must not be an empty chat interface.

Display contextual quick actions such as:

- Summarize portfolio risk.
- Explain the highest-risk companies.
- Compare selected companies.
- Analyze unusual signals.
- Generate report content.
- Explain how the risk score is calculated.
- Summarize changes during the selected period.

### Context-aware AI behavior

The assistant should receive relevant page context whenever the current API supports it.

Examples:

- On the HPG company page, the assistant should know that the user is viewing HPG.
- On the portfolio dashboard, it should analyze portfolio-level information.
- When the user has selected a 30-day range, that range should be included in the AI context.
- When companies are selected in a table, the assistant should be able to use those selections.
- When a risk category filter is active, include it when relevant.

Do not modify existing API contracts without a clear reason.

When the backend does not yet support contextual AI requests, create a clean frontend abstraction and clearly document the missing integration.

For example, define a typed context object that may contain:

- Current route.
- Current company.
- Selected companies.
- Time range.
- Active filters.
- User role.
- Visible dashboard metrics.

Do not send sensitive or unnecessary client-side information to the AI service.

### Mobile AI experience

On smaller screens:

- Keep the floating AI button in the bottom-right corner.
- Open the assistant as a bottom sheet or full-screen sheet.
- Include a drag handle when supported by the existing component library.
- Ensure the message input is not hidden by the virtual keyboard.
- Provide a clear close action.
- Respect mobile safe areas.
- Prevent background scrolling while the sheet is active.
- Avoid covering bottom navigation.

### AI interaction states

Handle all relevant states:

- Idle.
- Loading.
- Streaming, when supported.
- Success.
- Error.
- Retry.
- Empty response.
- Unauthorized.
- Timeout.
- Offline or unavailable.
- Rate limited.

Do not show only an indefinite spinner for long-running operations.

When supported by the real backend workflow, show meaningful processing stages such as:

- Collecting financial data.
- Identifying risk signals.
- Comparing historical changes.
- Generating an explanation.

Do not pretend that the backend performs steps it does not actually perform.

### Trust and explainability

Prepare the AI response interface to display:

- Data sources.
- Data timestamps.
- Confidence or reliability information.
- Metrics used in the analysis.
- “View evidence” links or expandable evidence sections.
- The relevant reporting period.
- A clear disclaimer that the output is not investment advice.

The assistant must avoid presenting buy or sell decisions as certain recommendations.

AI responses should distinguish between:

- Verified facts.
- Calculated metrics.
- Detected patterns.
- Model-generated interpretations.

---

## 7. Responsive design

Test at least the following viewport widths:

- `1440px`
- `1280px`
- `1024px`
- `768px`
- `390px`

Requirements:

- KPI cards should move from four columns to two columns and then one column.
- Charts must not overflow.
- Tables need a deliberate responsive strategy.
- The sidebar should become a drawer on mobile.
- The header must not break or overflow.
- Search may collapse into an icon or compact field on smaller screens.
- The floating AI button must not cover bottom navigation or important content.
- The AI panel should become a bottom sheet or full-screen sheet on mobile.
- Avoid unintended horizontal scrolling.

---

## 8. Accessibility requirements

Ensure:

- Semantic HTML.
- Full keyboard navigation.
- Visible focus indicators.
- `aria-label` attributes for icon-only buttons.
- Tooltips are not the only way information is communicated.
- At least WCAG AA color contrast.
- Risk levels are not communicated using color alone.
- Modals, drawers, and the AI panel use focus trapping.
- Pressing Escape closes the active panel when appropriate.
- Focus returns to the floating AI button after the assistant closes.
- Screen-reader-friendly chart summaries are available.
- The interface respects `prefers-reduced-motion`.
- Form inputs have proper labels.
- Error messages are connected to their relevant fields.

---

## 9. Data and interface states

Add or standardize:

- Loading skeletons.
- Empty states.
- Error states.
- Retry actions.
- Partial-data states.
- Permission-denied states.
- No-search-results states.
- Disabled states with explanations.
- Stale-data indicators.
- Offline states where relevant.

Never leave a large blank area when data is unavailable.

Example empty state:

“No companies have been added to this portfolio.

Add a company to begin monitoring financial health, receiving alerts, and generating reports.”

Suggested actions:

- Add company.
- Import from file, only if that function already exists.

---

## 10. Coding constraints

Follow these rules while editing:

- Do not break existing routes.
- Do not rename API fields without a migration plan.
- Do not inject mock data into the production flow.
- Do not remove current functionality.
- Do not add heavy dependencies when the existing stack can solve the problem.
- Do not duplicate existing components.
- Do not hard-code values that should come from props, configuration, or API responses.
- Do not create a single oversized dashboard component.
- Split the interface into focused, reusable components.
- Follow the project’s existing coding conventions.
- Preserve TypeScript strictness when TypeScript is used.
- Avoid `any` unless there is a documented reason.
- Avoid inline CSS when the project already uses a styling system.
- Do not modify the backend outside the task scope.
- Do not perform unrelated refactoring.
- Avoid breaking authentication and permission handling.
- Preserve internationalization patterns if the project uses them.
- Use existing primitives from the current component library before creating replacements.

---

## 11. Suggested component structure

Adapt this structure to the actual codebase. Do not force these exact names when the project already has suitable components.

- `AppShell`
- `Sidebar`
- `TopHeader`
- `SystemStatus`
- `DashboardHeader`
- `DisclaimerBanner`
- `MetricCard`
- `RiskTrendChart`
- `RiskDistribution`
- `PriorityCompanies`
- `RecentActivity`
- `EmptyState`
- `LoadingSkeleton`
- `FloatingAIAssistant`
- `AIAssistantButton`
- `AIAssistantPanel`
- `AIQuickActions`
- `AIMessage`
- `AISourceReferences`
- `AIContextProvider`

Do not place all AI functionality into one large file.

Separate:

- Presentation.
- Context collection.
- API communication.
- State management.
- Message rendering.
- Evidence rendering.

---

## 12. Implementation sequence

Work in the following phases.

### Phase 1: Audit

- Inspect the codebase.
- Identify affected files.
- Evaluate current UI/UX issues.
- Capture or describe the current visual state.
- Prepare a focused implementation plan.

### Phase 2: Design foundation

- Standardize design tokens.
- Improve typography.
- Improve spacing.
- Standardize buttons.
- Standardize cards.
- Standardize inputs.
- Standardize badges.
- Standardize tooltips.
- Add loading and empty-state patterns.

### Phase 3: Application shell

- Improve the sidebar.
- Improve the header.
- Simplify system status.
- Implement responsive navigation.

### Phase 4: Dashboard

- Improve the page header.
- Add KPI cards.
- Add charts.
- Add priority companies.
- Add recent activity or a meaningful empty state.

### Phase 5: Floating AI assistant

- Implement the floating button.
- Implement the desktop panel.
- Implement the mobile bottom sheet.
- Connect relevant page context.
- Implement loading, error, retry, and accessibility states.

### Phase 6: Verification

- Run the application.
- Run type checking.
- Run linting.
- Run existing tests.
- Run the production build.
- Inspect responsive layouts.
- Test keyboard navigation.
- Check browser console errors.
- Check failed network requests.
- Review visual consistency.

---

## 13. Required final output

After implementation, provide:

1. A summary of the UI/UX problems found.
2. A list of modified files.
3. An explanation of each major change.
4. A list of newly created components.
5. Any new dependencies and why they were necessary.
6. Missing backend or API integrations.
7. Build, lint, type-check, and test results.
8. Any incomplete areas.
9. Manual verification instructions.
10. Desktop and mobile screenshots, or detailed visual descriptions when screenshots are not supported.
11. Known limitations and recommended next steps.

Before claiming that the task is complete, run the appropriate project commands, including:

- Dependency installation when required.
- Lint.
- Type checking.
- Tests.
- Production build.

Do not claim that the application is complete, functional, or error-free unless those checks have actually been run.

---

## Acceptance criteria

The task is complete only when:

- The dashboard no longer contains a large meaningless empty area.
- Information hierarchy is clear.
- The interface feels like a modern Enterprise Fintech product.
- AI remains a supporting assistant rather than the primary product interface.
- The AI button is fixed in the bottom-right corner.
- The old “Analyze with AI” header button has been removed or replaced appropriately.
- The AI assistant opens as a side panel on desktop.
- The AI assistant opens as a bottom sheet or full-screen sheet on mobile.
- Existing functionality is preserved.
- The application is responsive.
- Loading, empty, error, and permission states are handled.
- Keyboard accessibility works.
- Type checking and the production build succeed.
- There are no critical console errors.
- No fake production data has been introduced.