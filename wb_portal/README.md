# WB HR Employee Portal (Odoo 18)

A modern employee self-service portal for **Odoo 18**, upgraded from the legacy
Odoo 16 `wb_portal` module. Includes **portal check-in / check-out with
geolocation**, **multi-language support**, a **per-user theme picker** and a
companion **admin theming module** (`wb_portal_theme`).

## Features & routes

| Feature | Route | Notes |
|---|---|---|
| Dashboard | `/home/` | profile hero, attendance stats, live check-in status card, leave balances, approval history |
| **Check In / Check Out** | `POST /attendance/checkin/` | geolocation verified (if configured), records lat/lng + mode `portal` |
| Attendance | `/attendance/` | date filter, month calendar, history table, check-in/out panel |
| Attendance PDF | `/attendance/func/` | PDF export with location column (respects the date filter) |
| Payslips | `/payslip/` | filterable list (graceful message if `hr_payroll` is not installed) |
| Payslip detail | `/payslipdetail/?pay_id=` | salary lines + gross/net summary |
| Payslip PDF | `/payslip/print/?pay_id=` | downloads the payslip PDF |
| Apply for time off | `/leaveform/` + `/leavesave/` (POST) | validates dates, friendly error messages |
| My time off | `/leaveview/` | list of own requests with status badges |
| Approve / refuse | `/leavesapproval/`, `/leave/approve/<id>`, `/leave/refuse/<id>` | managers only (with confirm dialog in JS) |
| All time off | `/leavesdisplay/` | HR only |
| Documents | `/documents/`, `/documents/upload/` (POST), `/web/binary/download_document` | upload / download personal documents |
| **User theme** | `POST /wb/theme/set` | per-user preset persisted in the session, floating palette button |
| **Notifications** | `POST /wb/notifications/read` | bell dropdown, unread badge, mark read (single / all) |
| **Planning** | `/planning/` | weekly / monthly shift view (native `planning`, Enterprise) |
| **Announcements** | `/announcements/` | company news from a Discuss channel (`discuss.channel`) |
| **Events** | `/events/` | upcoming events (native `event` module) |
| **Helpdesk** | `/helpdesk/` + `/helpdesk/new/` (POST) + `/helpdesk/<id>` | complaints & suggestions (native `helpdesk`, Enterprise) |
| **Expenses** | `/expenses/` + `/expenses/new/` (POST) | view own expenses and create / submit new ones |
| **Loans** | `/loans/` + `/loans/new/` (POST) | view own loans and apply for new ones (`wb.loan`) |

Plus:
- Automatic time off numbering (`TS/DD/MM/001`) via `hr.leave.sequence` field and an `ir.sequence`.
- **Leave Request Notification** email template (sent to `employee.leave_manager_id`).
- **Helpdesk (complaints & suggestions)**: view own tickets, submit new ones, see the conversation on each ticket.
- Website menu **My HR Portal** + **left sidebar navigation** (Dashboard, Attendance, Planning, Payslips, Time Off, Expenses, Loans, News, Events, Documents) with active-state highlighting and a user card.
- The sidebar shell (`wb_portal_layout`) is used by every page, so navigation and the notification bell are consistent everywhere; on mobile the sidebar becomes an off-canvas drawer with a hamburger + top bar.

## Check-in / check-out with location

- The attendance page (and the dashboard) show a **Check In / Check Out** button.
- When the button is pressed, the browser asks for the GPS position
  (`navigator.geolocation`) and sends it to `/attendance/checkin/`.
- **Work locations** (`hr.work.location`) can be configured with
  `latitude`, `longitude`, `geo_radius` (km) and `geo_enforced` in
  **Employees → Configuration → Work Locations** (new fields from this module).
  - If a work location has lat/lng + radius → the server computes the
    distance (haversine) and **refuses** the check-in/out when the employee is
    outside the radius.
  - If `geo_enforced` is also set → a location fix is mandatory (the check is
    refused when the browser cannot provide coordinates).
  - If nothing is configured → the check is allowed without verification.
- Every attendance row keeps an audit trail: `in_latitude/in_longitude` /
  `out_latitude/out_longitude` (core fields), `work_location_id` and
  `geo_verified` (new fields), plus `in_mode/out_mode = 'portal'`.

## Multi-language

- All user-facing strings live in the templates (translatable via
  **Settings → Translations**) or are wrapped in `_()` in the controllers.
- Starter translation files ship in `i18n/`: `wb_portal.pot` plus
  `ar.po` (Saudi Arabic), `ur.po` (Urdu), `hi.po` (Hindi) and `bn.po` (Bengali).
- Users switch language with the language selector in the portal footer
  (appears automatically once more than one language is active).
- To translate: **Settings → Translations → Languages** (activate e.g. Arabic,
  Urdu, Hindi, Bengali) → **Import/Export** to adjust the shipped translations
  or add your own.

## Notifications

An in-portal **notification center** (bell icon in the sub-navigation) keeps
employees and approvers informed without leaving the portal:

| Event | Who gets notified | Where it links |
|---|---|---|
| New time off request submitted | The employee's `leave_manager_id` (fallback: all Time Off users) | `/leavesapproval/` |
| Time off request approved | The employee | `/leaveview/` |
| Time off request refused | The employee | `/leaveview/` |
| Request passed first approval (two-step flow) | The employee | `/leaveview/` |

Mechanics:
- New model `wb.notification` (`user_id`, `title`, `body`, `type`, `read`, `url`,
  `related_model/id`) — plain rows, no extra access rights needed.
- `hr.leave` is hooked (`create`, `action_approve`, `action_validate`,
  `action_refuse`) so notifications fire **whether the request was made from the
  portal or from the backend**.
- The bell shows an **unread badge**, lists the 12 most recent notifications
  with relative time, supports **mark-one-read** (on click) and **mark all
  read**, and every row links to the relevant page.
- **Email**: the existing *Leave Request Notification* template is now actually
  sent (queued, non-blocking) to the leave manager when a request is created.
- **Browser notifications**: when a check-in/check-out succeeds and the user has
  granted browser notification permission, a native notification is shown
  (permission is requested lazily on the first check-in/out click).

Unread count and the notification list are rendered server-side on every portal
page, so the bell is always in sync.

## Planning / Announcements / Events / Expenses / Loans

### 1. Planning — `/planning/`
- Weekly / monthly view of the employee's shifts from the native **`planning`** module
  (Enterprise). Toggle *This Week* / *This Month*; each shift shows start/end time,
  role, project/task and state badge.
- The controller degrades gracefully when `planning` is not installed.

### 2. Announcements — `/announcements/`
- Fetches messages from a **Discuss channel**. The channel is resolved from the
  `ir.config_parameter` **`wb_portal.announcement_channel_id`** (set by an admin),
  otherwise the first channel named *Announcements* / *General* / *Staff* /
  *Company News* (exact match first), otherwise the first public channel.
- Pinned messages are shown first (treated as official announcements), then the
  most recent 30 comment/notification messages.

### 3. Events — `/events/`
- Upcoming events from the native **`event`** module, filtered to `date_begin >= now`,
  `active`, and (when the website mixin is installed) `is_published`.

### 4. Expenses — `/expenses/`
- Lists the employee's own `hr.expense` records (state badges: To Report / To Submit /
  Submitted / Approved / Done / Refused).
- **Create & submit** a new expense from the portal (description, date, category,
  amount, quantity). `employee_id` is forced server-side; `price_unit` and
  `total_amount` are passed together because the model recomputes `price_unit`
  from `total_amount / quantity` when no product is set.

### 5. Loans — `/loans/`
- Odoo has **no native loan module in 18**, so this module ships a secure
  `wb.loan` model (`LN/YYYY/NNNN` sequence, installments, repayment computation,
  approval workflow) with **backend views** for HR (Employees → Loans) and a
  portal apply form. The controller also works against an existing `hr.loan`
  model when one is installed (it detects the model and maps common fields).

### Security model
- **Reads**: every controller search is `sudo()` but always domain-filtered by the
  session employee (`('employee_id', '=', employee.id)`).
- **Detail pages**: none of these features expose a generic detail endpoint; the
  lists are the read surface, so no cross-employee leakage is possible.
- **Creates**: `employee_id` is always taken from the logged-in user server-side,
  never from the posted form.
- **Record rules**: `wb.loan` ships `ir.rule` records (employees → own records
  via `employee_id.user_id = user.id`; HR managers → all). For native modules
  (planning/event/hr_expense) the controller-level domains are the enforcement
  layer, avoiding conflicts with those apps' own access rules.

## Layout: left sidebar shell + top bar

All portal pages render inside `wb_portal_layout` (a wrapper around
`portal.frontend_layout`):

* **Top bar (always visible)**: a sticky app bar with a **hamburger toggle**
  (`wbSidebarToggle`, Bootstrap-compatible `aria-*` attributes), the current
  page title and the **notification bell**. Because the bell lives in the top
  bar (outside any scroll container), the notification tray is never clipped.
* **Desktop**: a fixed-width **left sidebar** (brand + grouped navigation +
  user card) next to the content column. The active page is highlighted with an
  accent bar. Clicking the **hamburger collapses / expands the sidebar** in
  place (`sidebar-collapsed`), so the portal menu really "collapses and
  expands correctly".
* **Mobile** (< 992px): the sidebar becomes an **off-canvas drawer**; the same
  hamburger opens it (backdrop click / Escape / nav click closes it).
* The website header (when the `website` module is installed) keeps its own
  responsive toggler for the site menu; the portal top bar is the toggler for
  the portal navigation.
* **Notification tray alignment**: the tray is positioned with
  `position: fixed` by JS, anchored to the bell and **clamped inside the
  viewport** (right/top computed from `getBoundingClientRect`), so it can never
  be cut off on the left edge. The sidebar itself no longer acts as a scroll /
  clip container (only `.wb-sidebar-nav` scrolls).
* Theming still works: CSS custom properties are declared on both `.wb-app`
  (the shell) and `.wb-page` (the content), so sidebar + content re-skin
  together for admin themes and user presets alike.

### 6. Helpdesk (complaints & suggestions) — `/helpdesk/`
- Lists the employee's own `helpdesk.ticket` records, filtered by
  `partner_id = user.partner_id` (never another employee's tickets).
- **Create & submit** a new ticket (subject, team, priority, description).
  `partner_id` and `email_from` are forced server-side from the session user.
- Each ticket links to a **detail page** showing its metadata and the
  conversation (`mail.thread` messages).
- Team list prefers website-enabled teams (`use_website = True`); priority and
  state options are read dynamically from the model's `selection` so they adapt
  to the installed helpdesk version.
- The `helpdesk` module is **Enterprise-only** in Odoo 18 — declared as a hard
  dependency; if it is missing the page shows a friendly message.

## Theming

Two layers:
1. **Per user** — the floating palette button (bottom-right) offers 5 presets
   (Indigo, Ocean, Emerald, Sunset, Midnight dark). The choice is stored in the
   session (`/wb/theme/set`) and applied instantly as CSS variables.
2. **Per database (admin)** — install the companion module **`wb_portal_theme`**
   and configure the global palette / custom primary color / corner radius in
   **Settings → HR Portal Theme**. A user's personal preset wins over the admin
   theme for that session.

The whole UI is driven by CSS custom properties on `.wb-page`, so themes never
break the layout — they only re-skin it.

## What changed vs. the Odoo 16 version

- Manifest rewritten for Odoo 18 (`assets` key, SPDX license).
- Controllers rewritten for the Odoo 18 APIs:
  - `ir.actions.report._render_qweb_pdf(report_ref, res_ids, data)` (old code
    passed a hard-coded `86`).
  - `@api.model_create_multi` in models.
  - `fields.Datetime.context_timestamp` for timezone-correct times.
  - Fixed `datetime.date(datetime.today())` crash, double `read()` in document
    upload, ownership checks on payslips/documents, CSRF-safe POST forms.
- Removed dead references (`hr.leave.all_employee_ids`, `remaining_leaves`,
  stale `models/website.py`, `time_off_appr_access`, old asset template).
- UI: complete redesign (gradient hero, stat cards, calendar, badges, progress
  bars, sub-navigation, check-in panel, theme picker).

## Notes for Odoo 18

- **`documents`** is Enterprise-only in Odoo 18 — hard dependency; on Community
  either remove it (see README notes in the previous version) or install a DMS.
- **`hr_payroll`** (payslips) is Enterprise-only; pages degrade gracefully.
- **`helpdesk`** is Enterprise-only too; `/helpdesk/` degrades gracefully when it is missing.
- Location checks need HTTPS (or `localhost`) for the browser Geolocation API.

## Installation

1. Copy `wb_portal` (and optionally `wb_portal_theme`) into your addons path.
2. Update the apps list and install **WB HR Employee Portal**.
3. Log in as an employee → **My HR Portal** menu (or `/home/`).
4. Optionally install **WB HR Portal Theme** and configure the look in
   **Settings → HR Portal Theme**.

## Verified on a real Odoo 18 instance

This module was installed and smoke-tested against **Odoo 18 (community + a
documents stub)**: a clean `-i wb_portal,wb_portal_theme` install succeeded and
every portal page returned 200 with the check-in/out, geolocation radius
enforcement, notification flows and admin theme switching exercised end-to-end
(see the git history / release notes for the bugs this surfaced and fixed).

Known fix in this release: the frontend asset (`portal.js`) previously imported
`whenReady` from `@web/core/utils/misc`, which **no longer exists in Odoo 18**
(that module now only exports `isEventHandled`/`markEventHandled`). It now
imports `whenReady` from `@odoo/owl`, matching core Odoo 18 modules. This
unblocks the login page and the frontend bundle (a failed module load there also
cascaded into "Missing template: web.Login user switch" errors). After
upgrading, do a hard refresh (Ctrl+Shift+R) to drop any cached bundle.

## Troubleshooting

### "The style compilation failed" banner (styling missing / unstyled toggle bar)

Odoo 18 compiles SCSS with **libsass**, which treats `min()` / `max()` as Sass
functions and **fails** on `min(340px, calc(100vw - 1.5rem))`. When that happens
the whole frontend bundle fails to compile and Odoo falls back to stale cached
styles — which is why new UI elements (like the top bar / hamburger) can appear
unstyled. This module no longer uses `min()`/`max()` in its SCSS (verified by
compiling the bundle with `sassc`).

If you still see the banner after upgrading, the old (failed) bundle may be
cached:
1. **Hard refresh** the browser (Ctrl+Shift+R / Cmd+Shift+R).
2. If it persists: **Settings → Technical → Clear caches** (or `--dev=all`
   while developing), then reload.
3. As a last resort restart the Odoo server.

### Helpdesk page error `KeyError: 'helpdesk.ticket.team'`

Some helpdesk installs / community replacements name the team model
differently (or ship `helpdesk.ticket` without a team model). The controller
now resolves the team model dynamically (from the ticket's `team_id` comodel,
then `helpdesk.ticket.team`, then `helpdesk.team`) and degrades gracefully:
if no team model exists, `/helpdesk/` still lists the employee's tickets and
shows a clear note instead of crashing. (Verified against a helpdesk build
without a team model.)

## Credits / license

LGPL-3. Built on Odoo `portal`, `website`, `hr`, `hr_attendance`, `hr_holidays`.
