# Student Ministry Command Center

TouchPoint **PyScriptForm** for Refuge / Student Ministry: weekly attendance, FY events, demographics, ministry outcomes, and small-group assignment.

| | |
|---|---|
| **App title** | Student Ministry Command Center |
| **Script** | [`StudentMinistryCentral.py`](StudentMinistryCentral.py) |
| **Requirements** | [`requirements.md`](requirements.md) |
| **User stories** | [`user-stories.md`](user-stories.md) |
| **Author** | Jake Pierson |
| **Runtime** | IronPython 2.7 inside TouchPoint |
| **Write risk** | Config JSON; Add to Tag; Small Group SubGroup assign/move. Attendance, notes, and baptisms are read-only. |

---

## Run

Special Content → **Python Scripts** → paste the script as `StudentMinistryCentral`.

```text
/PyScriptForm/StudentMinistryCentral
```

If the Special Content entry is renamed, links use `model.ScriptName`.

**Config (required for real numbers):** Special Content → **Text** → `StudentMinistryCentralConfig`  
Save once from the Admin **Config** tab to seed the file. Empty Org# / Program Id hides that tile instead of crashing.

---

## Roles

| Role | Access |
|------|--------|
| **(Staff or Elders) and Next Gen** | All work tabs |
| **View Only** (role name in Config) | Same tabs, no Tag / assign |
| **Admin** | Config tab |

Header: `#Roles=Access`

---

## Tabs

- **Home** — FY decisions, baptisms, weekly + monthly attendance deltas, FY event count, unique/raw enrollments, event list (past grey / upcoming Azure), leader tiles
- **Volunteers** — Leader / Student Leader / Coach rosters + launch Volunteer Onboarding
- **Demographics** — Age, grade, school (`People.SchoolOther`), month birthdays, master roster
- **Ministry** — Stories, baptisms, decisions, Kids/Awana vs 6th census, grade-to-grade census, Senior Year placeholder, serving outside Refuge
- **Small Groups** — VBS-style cards + assign panel (create / add / move; same SubGroup name on student + leader orgs)
- **Config** — Org#s, Program/Division, keywords, URLs

Event **name** opens `/Org/{id}`. Chart **icon** opens `/PyScriptForm/InvolvementDashboard?org_id={id}`.

Every people list is sortable and can **Add to Tag**. Names open `/Person2/{id}`.

---

## Fiscal year

July 1 – June 30.

---

## First-time setup

1. Paste the Python script.
2. Open the dashboard as Admin → Config.
3. Enter MS/HS Org#s, Student Ministry Program Id, three leader Org#s, Kids/Awana Program Ids.
4. Save. Confirm tiles populate.
5. Audit Volunteer Program Id / extra Org#s before trusting “serving outside Refuge.”
