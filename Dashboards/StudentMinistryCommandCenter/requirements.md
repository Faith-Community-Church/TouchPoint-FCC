# Student Ministry Command Center — Requirements

Capture-only doc; open questions marked **TBD**. Update as decisions land.

**Companion:** [user-stories.md](user-stories.md) — keep both in sync.

## Goal

Staff-facing TouchPoint Special Content (Python) command center for **Refuge / Student Ministry**. Operators see weekly health, FY events, demographics, ministry outcomes, and small-group assignments in one place.

**Not** Volunteer Onboarding. That pipeline stays in `VolunteerOnboardingDashboard`. This tool lists current leaders and **launches** that dashboard.

**No Events work surface.** Event registration, payments, allergies, and contacts are handled by Involvement Dashboard. Home only lists FY events and deep-links out.

**Aesthetic template:** VBS Home Base / Awana / Volunteer Onboarding (dark navy header `#001429`, white cards, soft borders/shadows, segmented pill tabs). Brand names in conversation; **hex in the file**.

---

## Architecture (confirmed)

| Layer | Role |
|-------|------|
| **Dashboard** | Sole operator UI (Special Content → Python) |
| **Weekly source** | Standing Middle School + High School involvements (meetings + enrollment) |
| **Event source** | Standalone involvements in Student Ministry **Program / Division** |
| **Leader sources** | Hard-coded Involvements: Volunteer Leaders, Student Leaders, Small Group Coaches |
| **Event detail** | `/Org/{id}` (new tab) and `/PyScriptForm/InvolvementDashboard?org_id={id}` (icon) |
| **Volunteer pipeline** | `/PyScriptForm/VolunteerOnboardingDashboard` (launch only) |
| **Config** | Admin Settings tab; Special Content JSON (portable). Script defaults if missing |
| **Small groups** | MemberTags / SubGroups; **same tag name** on leader org + student org(s) |

### Config storage

**Special Content JSON** (same pattern as Volunteer Onboarding: `WriteContentText` / content name `StudentMinistryCentralConfig`). One blob, easy backup, Org# / Prog / Div changes are field edits.

Do **not** store primary config as Ad Hoc Extra Values on involvements.

---

## Navigation & access (confirmed)

Top pills. **Admin** sees Config.

Role logic (same family as other Next Gen tools): `(Staff OR Elders) AND Next Gen` **or** Admin.

| Tab | Who | v1 |
|-----|-----|----|
| Home | Area access | Yes |
| Volunteers | Area access | Yes |
| Demographics | Area access | Yes |
| Ministry | Area access | Yes |
| Small Groups | Area access; write = not View Only | Yes |
| Config | Admin | Yes |

**View Only** — existing church role picker in Config. Those users see every list and tile but cannot assign subgroups or Add to Tag.

Header: `#Roles=Access`. Finer gates in code.

---

## Fiscal year

Ministry / fiscal year = **July 1 – June 30**.

“Current FY” as of today (e.g. 2026-09-21) = **2026-07-01 through 2027-06-30**.

All FY tiles (events, unique/raw enrollments, baptisms, decisions **if FY-scoped**) use this window. **TBD:** whether Decisions and Stories of Transformation are FY-scoped or all-time (recommend **FY-scoped** for Home tiles; Ministry tab can filter).

---

## v1 tabs

### 1. Home

Everything below is v1.

#### Decisions
- Count of people who have a **non-archived** TaskNote whose keywords include **both**:
  - `Decision to Follow Jesus`
  - `Refuge Student Ministry`
- **TBD:** AND vs OR if a note only has one of the two; recommend **AND**.
- **TBD:** FY filter on `TaskNote.CreatedDate` (recommend yes for Home tile).
- Query pattern already used in Volunteer Onboarding: `TaskNote` → `TaskNoteKeyword` → `Keyword.Description`.

#### Baptisms
- Count of people with `People.BaptismDate` **in the current FY**.
- **TBD:** restrict to students (enrolled on standing MS/HS, or age/grade range) vs any person with a FY baptism. Recommend **enrolled on standing MS and/or HS** (or Config “baptism people scope” org set).

#### Weekly attendance (standing MS + HS meetings)
Present = `Attend.AttendanceFlag = 1` on configured weekly orgs (VBS `_attend_present_count` pattern).

| Metric | Rule |
|--------|------|
| This week | Distinct present PeopleIds on meetings whose `MeetingDate` falls in the current ministry week |
| Week-over-week delta | This week minus last week (count and %). Show `+` / `–` / flat |
| Last-year same week | This week minus the meeting week **52 weeks earlier** (same weekday window). **TBD:** calendar-week vs “Nth Refuge week of FY” |
| Month average | Mean of weekly present counts in the current calendar month (or FY month — **TBD**, recommend calendar month) |
| vs last month avg | This month avg minus previous calendar month avg |
| vs last year same month | This month avg minus same calendar month last year |

**TBD:** Combined MS+HS only vs stacked/split tiles. Recommend **combined headline + MS / HS split**.

**TBD:** “Week” start day (Sunday vs Wednesday night). Config: `week_start_dow`.

Show people drill-down from each attendance number (list + Add to Tag).

#### FY events (Prog/Div discovery)
Discover involvements where Program (and optional Division set) match Config. **Exclude** standing MS/HS Org#s and the three leader orgs so weekly/leader orgs are not counted as events.

| Metric | Rule |
|--------|------|
| Event count since July 1 | Involvements in the discovery set whose **start** is on/after FY start. Start = `FirstMeetingDate` if set, else `Organization.CreatedDate` (**TBD** confirm) |
| Unique enrollments | `COUNT(DISTINCT PeopleId)` across `OrganizationMembers` on those FY event orgs (current members; **TBD:** include dropped via `EnrollmentTransaction` in FY?) |
| Raw enrollments | `COUNT(*)` of membership rows on those FY event orgs (one person on three events = 3) |

#### Ministry-year event list
- All discovered events that belong to the current FY (same start rule as count).
- **Past** = last meeting / end date **before today** → grey (muted, not Vermillion).
- **Upcoming** (or in progress) → **Azure**.
- Event **name** → `/Org/{OrganizationId}` new tab.
- **Dashboard icon** → `/PyScriptForm/InvolvementDashboard?org_id={OrganizationId}` new tab (script path Config-mappable).
- Sort: upcoming first by start date, then past (most recent past first). **TBD.**

**TBD:** in-progress events (started, not ended) — treat as upcoming/Azure.

**TBD:** primary `Organizations.DivisionId` only vs also `DivOrg` extra divisions.

#### Leader tiles (hard-coded involvements)
| Tile | Source |
|------|--------|
| Volunteer leaders | Member count on Config Org# **Volunteer Leaders** |
| Student leaders | Member count on Config Org# **Student Leaders** |
| Small Group Coaches | Member count on Config Org# **Small Group Coaches** |

Each tile drills to that org’s roster (or Volunteers tab). Org#s are Config fields with FCC defaults once known.

---

### 2. Volunteers

- Roster of the **Volunteer Leaders** involvement (name, age/grade if useful, subgroups, profile link).
- Button / tile: **Open Volunteer Onboarding** → `/PyScriptForm/VolunteerOnboardingDashboard` (optional `?area=student` if that query still works).
- Do **not** rebuild application / BC / handbook steps here.
- Sortable, filterable, Add to Tag.

**TBD:** also show Student Leaders and Coaches as sub-lists on this tab, or Home tiles only. Recommend **sub-lists** on Volunteers (Leaders / Student Leaders / Coaches) so the tab matches the three Home tiles.

---

### 3. Demographics

People scope = current members of standing **MS and HS** orgs (union, distinct). **TBD:** include event-only students? Recommend **weekly orgs only** for master roster.

| Block | Rule |
|-------|------|
| Age breakdown | `People.Age` buckets. **TBD:** exact buckets (e.g. 11–12, 13–14, 15–16, 17–18, 19+) |
| Grade breakdown | `lookup.GradeLevel` via `OrganizationMembers.GradeLevelId` then `People.GradeLevelId` (same COALESCE as Involvement Dashboard) |
| School breakdown | Source **TBD**. First candidate: `People.SchoolOther`. Audit RecReg / Extra Values before locking |
| Upcoming birthdays | `People.BirthDay` + `BirthMonth` in the **current calendar month** (ignore year). List name, date, age turning. Sort by day |
| Master roster | One table: name, grade, gender, age, school. Filters: **grade**, **gender**. Sortable columns |

---

### 4. Ministry

| Block | Rule |
|-------|------|
| Stories of Transformation | Notes with keyword **`Stories of Transformation`** (**TBD** exact Description). Count + name list. FY filter **TBD** (recommend yes) |
| Baptisms | Same people as Home baptism tile; count + name list + BaptismDate |
| Decisions | Same notes as Home decisions tile; name list (one row per person, latest note date) |
| Attrition: Faith Kids / Awana → 6th | Compare prior-year Kids/Awana enrollment (Config **Program / Division** for Faith Kids + Awana) to current 6th-grade enrollment on standing student orgs. Rate = (prior cohort still present) / (prior cohort size). **TBD:** cohort = last FY 5th graders vs anyone who was on those orgs and would now be grade 6 |
| Attrition: adjacent grades | For each pair 6→7, 7→8, 8→9, 9→10, 10→11, 11→12: of people who were grade N last year (or last FY members at grade N), how many are grade N+1 and still enrolled. **TBD:** snapshot method (current `GradeLevel` vs `EnrollmentTransaction` + grade at drop) |
| Senior Year of Discipleship | **Placeholder.** v1 = enrollment count on a Config Org# (0 = hide number, show “Coming soon”) |
| Students serving outside Refuge | Distinct people who are members of standing Refuge (MS/HS) **and** any Involvement in Config **Volunteer Program** (Prog/Div and/or Org# allow-list). **Must audit** so guest-services / worship / kids / student-leader orgs are complete. v1 ships with Config list + a “needs audit” note on the tile |

---

### 5. Small Groups

Nested on this tab:

1. **Group cards** — same idea as VBS Home Base “By Group”: each SubGroup name, assigned **leaders** (from Volunteer Leaders / Coaches / Student Leaders who share that tag), student count, printable-ish card.
2. **Assign panel** — VBS Assign analog:
   - Master list of weekly-org students, filter **grade** and **gender**.
   - Assign leaders from the Leader involvement(s).
   - **Same SubGroup syntax across involvements** (`model.AddSubGroup(peopleId, orgId, name)` on MS, HS, and leader orgs). Creating “Harbor 7B” creates/uses that MemberTag name on every configured org.
   - **Define a new subgroup** if it does not exist (registry + `AddSubGroup`; VBS JsonDocumentRecords registry or Config JSON group list).
   - **Move** a student from group A to group B (remove A tag, add B on the student org).
   - **Multiple subgroups** allowed on one person (do **not** always clear all group tags on assign). Move is explicit; “add to another group” is a separate action.
   - View Only cannot write.

**TBD:** one shared group namespace vs MS-only / HS-only groups. Recommend **one namespace**, filter cards by whether the group has anyone on MS, HS, or both.

---

## List, sort, filter, tag (global)

Applies to **every people list** (Home drills, Volunteers, Demographics roster, Ministry lists, Small Group members):

- Sortable columns (click header).
- Filterable (at least text search; grade/gender where those columns exist).
- Person **name** → `/Person2/{PeopleId}` new tab.
- **Add to Tag** — same modal + `add_to_tag` action as Awana / Involvement Dashboard / VBS (`model.AddToTag` / existing helper). Hidden for View Only.

---

## Admin Config

Expand/collapse sections.

- Standing orgs: MS Org#, HS Org#
- Weekly attendance: which of those orgs count; `week_start_dow`
- Event discovery: Program Id, Division Id(s); exclude-org list (auto-include standing + leader orgs)
- Event start-date field (`FirstMeetingDate` vs `CreatedDate`)
- Leader orgs: Volunteer Leaders, Student Leaders, Small Group Coaches
- Volunteer Onboarding URL
- Involvement Dashboard URL (`/PyScriptForm/InvolvementDashboard`)
- Note keywords: Decisions (two names), Stories of Transformation
- Baptism scope (org set)
- Attrition: Kids / Awana Program + Division Ids
- Senior Year Org# (0 = placeholder)
- Serving-outside: Volunteer Program Id / Division Ids / extra Org#s
- Small-group orgs that receive the same tag names
- View Only role
- Age buckets (optional)

Empty Org# / Prog Id → hide the dependent tile, do not crash.

---

## Codebase notes (bvcms / FCC)

- **Notes:** `dbo.TaskNote`, `dbo.TaskNoteKeyword`, `dbo.Keyword` — see `VolunteerOnboardingDashboard._has_keyword_note`.
- **Baptism:** `People.BaptismDate` (`CmsData/Generated/Person.cs`).
- **Grade:** `lookup.GradeLevel` on `People.GradeLevelId` and `OrganizationMembers.GradeLevelId` — Involvement Dashboard COALESCE.
- **School (candidate):** `People.SchoolOther` (`nvarchar(100)`). Confirm vs RecReg / EV before build.
- **Attendance:** `dbo.Attend` + `AttendanceFlag = 1`; VBS `_attend_present_count`.
- **Prog/Div:** `Organizations.DivisionId` → `Division.ProgId` → `Program` (Awana `_org_brief`). Confirm `DivOrg`.
- **SubGroups:** `MemberTags` + `OrgMemMemTags`; write via `model.AddSubGroup` / remove counterpart (VBS `_assign_group`).
- **Add to Tag:** Awana / VBS / Involvement Dashboard `action=add_to_tag`.
- **Involvement Dashboard deep link:** `/PyScriptForm/InvolvementDashboard?org_id=123`.
- **Org page:** `/Org/{id}`.

IronPython 2.7: `model.Form` on GET, `model.DynamicData()` params, token replace not `.format()` on large HTML, `_s()` / no `unicode(byte)` default, no f-strings.

---

## Out of scope (v1)

- Rebuilding event registration / finance / allergies UI (use Involvement Dashboard).
- Volunteer application / BC / handbook checklist.
- Senior Year of Discipleship beyond a count placeholder.
- Writing attendance or baptism dates from this tool.
- Product changes in the bvcms repo.

---

## Open questions

| ID | Topic | Recommendation |
|----|--------|----------------|
| Q1 | Decision keywords AND vs OR | AND both keywords |
| Q2 | Decisions / stories FY-scoped? | Yes on Home; Ministry filterable |
| Q3 | Baptism people scope | Standing MS/HS members |
| Q4 | Week start | Config; default Wednesday or Sunday after audit |
| Q5 | Last-year week match | 52-week offset |
| Q6 | Event start field | `FirstMeetingDate` then `CreatedDate` |
| Q7 | Unique enrollments include drops? | Current members only for v1 |
| Q8 | School source | Audit `SchoolOther` vs RecReg / EV |
| Q9 | Attrition cohort definition | Last FY members at grade N still present at N+1 |
| Q10 | Serving-outside org list | Audit required before lock |
| Q11 | DivOrg vs primary Division | Primary first; add DivOrg if events are missed |
| Q12 | Volunteers tab sub-lists | Leaders + Student Leaders + Coaches |
| Q13 | Age buckets | 11–12 / 13–14 / 15–16 / 17–18 / 19+ |
| Q14 | Shared vs MS/HS group namespaces | One shared SubGroup name |

None of these block writing the docs or scaffolding the shell.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-09-21 | Initial capture: command center; events via Prog/Div; no Events tab; Home metrics; Volunteers; Demographics; Ministry; Small Groups; weekly attendance + YoY |
| 2026-09-21 | v1 scaffold: `StudentMinistryCommandCenter.py` + README |
| 2026-09-21 | Renamed script to `StudentMinistryCentral.py`; config `StudentMinistryCentralConfig` |
