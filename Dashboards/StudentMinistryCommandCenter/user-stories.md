# Student Ministry Command Center — User Stories

Companion to [requirements.md](requirements.md).
Update **both** docs when scope changes. Stories are the “who/why”; requirements
hold field names, Org#s, Prog/Div, and technical rules.

**Status key:** `v1` = first ship · `later` = post-v1 · `infra` = platform

**Personas**
- **Ministry Leader** — Staff/Elders + Next Gen (or Admin); can write Small Groups and Add to Tag
- **View-Only User** — Config View Only role; sees tiles and lists; cannot write
- **Admin** — all tabs + Config

---

## Epic A — Access, navigation, config

### US-A1 — See the command center `v1` `infra`
**As a** Ministry Leader
**I want** Home, Volunteers, Demographics, Ministry, Small Groups (and Config if Admin)
**So that** I work Student Ministry from one branded tool.

**Acceptance**
- Pills match VBS / Awana family (Black Pearl header, Downriver / Azure)
- Tab visible only if role gate passes
- No Events work-surface tab

### US-A2 — Admin configures sources `v1` `infra`
**As an** Admin
**I want** a Config tab for standing orgs, Prog/Div, leader Org#s, keywords, and URLs
**So that** I do not edit Python to remap involvements.

**Acceptance**
- Stored as Special Content JSON (`StudentMinistryCentralConfig`)
- Empty Org# / Prog Id hides the dependent tile; script does not crash
- View Only = existing role picker

### US-A3 — View-only access `v1`
**As a** View-Only User
**I want** to see every tile and list
**So that** I can monitor without changing tags or subgroups.

**Acceptance**
- Assign / Add to Tag hidden or disabled

---

## Epic B — Home

### US-B1 — Decisions this year `v1`
**As a** Ministry Leader
**I want** a count of Decision notes tagged `Decision to Follow Jesus` **and** `Refuge Student Ministry`
**So that** I see evangelism fruit without a search.

**Acceptance**
- Non-archived TaskNotes; FY on CreatedDate (Q1/Q2 in requirements)
- Tile drills to a people list (name → profile, Add to Tag)

### US-B2 — Baptisms this FY `v1`
**As a** Ministry Leader
**I want** a count of profile Baptism Dates in the current July–June FY
**So that** I see baptisms without exporting People.

**Acceptance**
- `People.BaptismDate` in FY; scope TBD (recommend standing MS/HS)
- Drill-down list with dates

### US-B3 — This week’s attendance + deltas `v1`
**As a** Ministry Leader
**I want** this week’s present count, week-over-week delta, and last-year same-week comparison
**So that** I know if Refuge is up or down.

**Acceptance**
- Present = `AttendanceFlag = 1` on standing MS/HS meetings
- Show count, WoW delta, last-year week delta (count and %)
- Drill-down to who was present

### US-B4 — Monthly attendance averages `v1`
**As a** Ministry Leader
**I want** this month’s average attendance, delta vs last month, and vs the same month last year
**So that** I can talk year-over-year performance in staff meeting.

**Acceptance**
- Month avg from weekly present counts
- Last-month and last-year-same-month deltas

### US-B5 — FY event volume `v1`
**As a** Ministry Leader
**I want** how many Student Ministry events started since July 1
**So that** programming load is visible on Home.

**Acceptance**
- Discovery = Config Program / Division, excluding weekly + leader orgs
- Start date rule per requirements Q6

### US-B6 — Event enrollment totals `v1`
**As a** Ministry Leader
**I want** unique people enrolled across FY events **and** raw enrollment rows
**So that** I can tell “how many students touched an event” vs “how many sign-ups.”

**Acceptance**
- Unique = distinct PeopleId; raw = membership row count
- Each number drills to a list (raw list may repeat a person per event)

### US-B7 — Ministry-year event list `v1`
**As a** Ministry Leader
**I want** every FY event listed: past grey, upcoming Azure
**So that** I see the year at a glance.

**Acceptance**
- Event name → `/Org/{id}` new tab
- Icon → `/PyScriptForm/InvolvementDashboard?org_id={id}` new tab
- No in-tool registration/finance UI

### US-B8 — Leader headcounts `v1`
**As a** Ministry Leader
**I want** tiles for Volunteer Leaders, Student Leaders, and Small Group Coaches
**So that** staffing is visible next to student metrics.

**Acceptance**
- Counts from the three Config Org#s
- Click through to that roster

### US-B9 — Modern, on-brand Home `v1` `infra`
**As a** staff user
**I want** Home to match VBS Home Base / Awana branding
**So that** it feels like a first-class FCC tool.

---

## Epic C — Volunteers

### US-C1 — See current leaders `v1`
**As a** Ministry Leader
**I want** the Volunteer Leaders involvement listed on a Volunteers tab
**So that** I know who is already serving.

**Acceptance**
- Sortable / filterable roster; name → profile; Add to Tag
- Recommend sub-lists for Student Leaders and Coaches (Q12)

### US-C2 — Launch onboarding `v1`
**As a** Ministry Leader
**I want** a button that opens Volunteer Onboarding
**So that** new leader intake stays in the existing pipeline.

**Acceptance**
- `/PyScriptForm/VolunteerOnboardingDashboard` (new tab)
- No application / BC / handbook steps in this tool

---

## Epic D — Demographics

### US-D1 — Age, grade, school mix `v1`
**As a** Ministry Leader
**I want** breakdowns of standing MS/HS members by age, grade, and school
**So that** I can staff and communicate by slice.

**Acceptance**
- Grade = Involvement Dashboard GradeLevel COALESCE
- School source marked TBD (`SchoolOther` first candidate)
- Each bar/row drills to people

### US-D2 — Birthdays this month `v1`
**As a** Ministry Leader
**I want** upcoming (this calendar month) birthdays
**So that** we can celebrate students.

**Acceptance**
- Match month; sort by day; show name + date + age turning

### US-D3 — Master roster `v1`
**As a** Ministry Leader
**I want** one filterable roster (grade + gender) of weekly-org students
**So that** I can build tags and small groups from the same list.

**Acceptance**
- Sortable columns; name → profile; Add to Tag
- Filters: grade, gender, text search

---

## Epic E — Ministry outcomes

### US-E1 — Stories of Transformation `v1`
**As a** Ministry Leader
**I want** a count and name list from the Stories of Transformation keyword
**So that** I can share names in staff/elder settings.

### US-E2 — Baptism and decision lists `v1`
**As a** Ministry Leader
**I want** the Home baptism and decision numbers as named lists
**So that** follow-up is a click, not a search.

### US-E3 — Kids / Awana into 6th grade `v1`
**As a** Ministry Leader
**I want** attrition (or retention) from Faith Kids / Awana into 6th grade
**So that** we see the Next Gen handoff.

**Acceptance**
- Kids/Awana side via Config Prog/Div
- Rate + drill-down: still here vs missing
- Cohort rule TBD (Q9)

### US-E4 — Grade-to-grade attrition `v1`
**As a** Ministry Leader
**I want** 6→7, 7→8, … 11→12 retention
**So that** we know where we lose students.

**Acceptance**
- One rate per adjacent pair; drill to retained / lost

### US-E5 — Senior Year of Discipleship placeholder `v1`
**As a** Ministry Leader
**I want** a visible placeholder (enrollment count if Org# set)
**So that** the program has a home before the full design exists.

### US-E6 — Serving outside Refuge `v1`
**As a** Ministry Leader
**I want** students enrolled in Refuge **and** a volunteer-program involvement
**So that** we celebrate students who serve the church.

**Acceptance**
- Config Prog/Div + Org allow-list; audit note until the list is complete

---

## Epic F — Small Groups

### US-F1 — See groups with leaders `v1`
**As a** Ministry Leader
**I want** cards like VBS By Group: group name, leaders, student count
**So that** I can see coverage at a glance.

### US-F2 — Filter the assign list `v1`
**As a** Ministry Leader
**I want** the assign panel’s master list filtered by grade and gender
**So that** I can build a 7th-grade girls group without scanning everyone.

### US-F3 — Create a subgroup `v1`
**As a** Ministry Leader
**I want** to define a new SubGroup name if it does not exist
**So that** I am not stuck in Involvement → Subgroups first.

**Acceptance**
- Same name applied on configured student + leader orgs

### US-F4 — Assign and move `v1`
**As a** Ministry Leader
**I want** to put a student or leader in a group and move them later
**So that** mid-year changes do not require Org admin.

**Acceptance**
- Move = remove old group tag, add new (on that person’s student org)
- Leaders assigned from the Leader involvement(s)

### US-F5 — Multiple subgroups `v1`
**As a** Ministry Leader
**I want** a student to belong to more than one SubGroup
**So that** a student can sit in a midweek group and a Sunday group.

**Acceptance**
- Assign-add does not clear other group tags
- Move remains an explicit replace

---

## Epic G — Lists everywhere

### US-G1 — Sort and filter `v1` `infra`
**As a** Ministry Leader
**I want** every people list sortable and filterable
**So that** I can work a queue without exporting.

### US-G2 — Open a profile `v1` `infra`
**As a** Ministry Leader
**I want** every name to open the person record in a new tab
**So that** I never lose my place.

### US-G3 — Add to Tag `v1` `infra`
**As a** Ministry Leader
**I want** Add to Tag on every people list
**So that** I can email, text, or run a search from the dashboard.

**Acceptance**
- Same modal pattern as Awana / VBS / Involvement Dashboard
- Hidden for View Only

---

## Epic H — Later

### US-H1 — Richer Senior Year program `later`
Full discipleship track beyond an enrollment count.

### US-H2 — Enrollment history / trends `later`
`EnrollmentTransaction` unique-event history across years.

### US-H3 — Attendance writeback `later`
Mark present/absent from this tool (v1 is read-only on meetings).

### US-H4 — In-tool event ops `later`
Only if Involvement Dashboard is not enough. Not v1.

---

## Traceability (story ↔ requirements)

| Story | Requirements anchors |
|-------|----------------------|
| US-A* | Architecture, Navigation, Config |
| US-B* | Home tiles, FY events, attendance, leader tiles |
| US-C* | Volunteers tab |
| US-D* | Demographics |
| US-E* | Ministry tab |
| US-F* | Small Groups + VBS assign |
| US-G* | Global list / tag / profile rules |
| US-H* | Out of scope / later |

---

## Revision log

| Date | Change |
|------|--------|
| 2026-09-21 | Initial stories from revised v1 (Home + Volunteers + Demographics + Ministry + Small Groups; no Events tab) |
| 2026-09-21 | Build started: StudentMinistryCommandCenter.py v1 scaffold |
| 2026-09-21 | Renamed script to StudentMinistryCentral.py |
