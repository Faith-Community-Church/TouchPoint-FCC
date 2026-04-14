# TouchPoint for FCC

## What is this?

This repository stores the scripts that power reports, dashboards, and automated workflows inside FCC's TouchPoint database platform.

TouchPoint is the system FCC uses to manage people, groups, involvement, and ministry activity. While TouchPoint provides a lot out of the box, this collection of scripts extends what it can do — giving staff and volunteers better visibility into data, cleaner reports, and more streamlined workflows tailored specifically to how FCC operates.

Think of this repo as the source of truth for any custom work built on top of TouchPoint. If a report exists, it lives here. If a dashboard was built, it lives here. If a workflow was automated, it lives here.

---

## Who is this for?

This repo is primarily maintained by FCC's IT staff. However, it is written and organized so that future staff, volunteers, or vendors can understand what exists, what it does, and how to use it — without needing a technical background.

If you are looking for a specific report or dashboard and are not sure where to find it, start with the folder structure below.

---

## What's in here?

| Folder | What it contains |
|--------|-----------------|
| `Reports/` | Scripts that pull and export data from TouchPoint |
| `Dashboards/` | Visual dashboards and charts for staff use |
| `SQLqueries/` | Standalone SQL queries for data lookups |
| `Widgets/` | Embeddable UI components used inside TouchPoint pages |
| `HTMLsnippets/` | Small HTML components used in email templates and registration forms |
| `OnEnrollScripts/` | Actions that bolt on to registration processes — triggered automatically during enrollment |
| `_templates/` | Starting points for building new scripts — not for direct use |

Each script folder contains a `README.md` that explains in plain English what the script does, how to run it, and anything important to know before using it.

---

## How scripts work in TouchPoint

TouchPoint has a built-in shell that allows authorized administrators to run Python, SQL, and HTML scripts directly inside the platform. Scripts in this repo are designed to be copied and pasted into that shell to run.

**No technical installation is required to use these scripts.** You just need:
- Admin access to TouchPoint
- The script contents from this repo
- Instructions from the script's README

---

## Important notes

- **Scripts are read-only by default.** Most scripts only retrieve and display data — they do not change anything in the database.
- **Scripts that modify data are clearly marked.** Any script that updates or changes records will say so in its README under "Write Risk."
- **Never run a script you don't understand.** If you are unsure what a script does, ask IT before running it.

---

## For technical contributors

### Languages used
- Python — reports and data logic
- SQL (T-SQL / Microsoft SQL Server) — data queries
- HTML / CSS — dashboards and widgets

### Adding a new script
1. Copy the appropriate template from `_templates/`
2. Rename the folder using `camelCase` (e.g. `monthlyGivingReport/`)
3. Name script files to match the folder (e.g. `monthlyGivingReport.py`)
4. Place it in the correct parent folder (`Reports/`, `Dashboards/`, `SQLqueries/`, `Widgets/`, `HTMLsnippets/`, or `OnEnrollScripts/`)
3. Update the header comment in the script file
4. Fill in the `README.md` inside the folder
5. Commit using Conventional Commits format (see below)
6. Open a Pull Request to `main`

### Commit conventions

| Prefix | Use for |
|--------|---------|
| `feat:` | Adding a new script or feature |
| `fix:` | Fixing a broken script |
| `chore:` | Maintenance — no functional change |
| `docs:` | README or documentation updates |
| `refactor:` | Restructuring without behavior change |
| `ci:` | GitHub Actions workflow changes |

### Branching
```
main                  # Always stable — never commit directly
└── feature/name      # New scripts or features
└── fix/name          # Bug fixes
```

### CI checks
Every push runs automated checks:
- Python syntax and style (flake8)
- SQL formatting and syntax (sqlfluff)
- HTML validation (html-validate)
- Secret scanning (Trufflehog)

---

## Questions?

Contact FCC IT for access, questions about specific scripts, or to request a new report or dashboard.
