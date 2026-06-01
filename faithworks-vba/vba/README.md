# FaithWorks Planning Tool — VBA Source

VBA modules extracted from `FaithWorksPlanningMaster_2026.xlsm`.

## Module Overview

| File | Purpose |
|---|---|
| `Constants.bas` | All shared constants — sheet names, column headers, colors, font sizes. **Start here when changing field names or colors.** |
| `ImportModule.bas` | Core import from TouchPoint export. Builds the header→column map stored in the Parameters sheet. |
| `MailMergePrintModule.bas` | Connects to Word via COM and runs the volunteer card mail merge. |
| `PrintJobModule.bas` | Prints all participants assigned to a specific job number. |
| `PrintJobDayModule.bas` | Prints participants grouped by job, filtered to a weekday. |
| `PrintParticipantsJobDayModule.bas` | Prints a name+job roster for a selected day. |
| `StyleModule.bas` | Applies fonts, borders, row heights, and column widths to the participant sheet. |
| `SetShapes.bas` | Creates/recreates the Import and Print buttons in the header band. |
| `ButtonActions.bas` | OnAction targets wired to the header buttons. |
| `SharedPrintHelpers.bas` | Shared utilities: get participant sheet, create temp sheet, print + cleanup. |
| `JobDayClass.bas` | Lookup object — resolves a day name (Mon–Fri) to a column index. |
| `JobNumbersModule.bas` | Builds a sorted deduplicated list of all job numbers across all 5 days. |
| `CollectUniqueValues.bas` | Returns unique values from a range as a Collection. |
| `SortCollectionModule.bas` | Bubble sort for VBA Collections. |
| `LoadImportDataModule.bas` | Backward-compatibility stub — delegates to ImportModule. |
| `ThisWorkbook1.bas` | Double-click handler — toggles color highlight on Mon–Fri availability cells. |
| `TestModule.bas` | Unit tests for GetMappedColumn, SortCollection, and CreateUniqueJobNumberList. |
| `JobListBox.frm` | Print dialog UserForm — combo boxes for day/job selection + Print Cards button. |
| `ImportButton.frm` | Simple one-button import UserForm. |

## How Header Matching Works

All TouchPoint column headers are defined as constants in `Constants.bas`. On import, `ImportModule` scans the header row, builds a name→column-index dictionary, and persists it to the Parameters sheet (rows 200–260). Every other module calls `ImportModule.GetMappedColumn("Header Name")` at runtime — no hardcoded column letters anywhere.

To add a new column (e.g. Join Date):
1. Add a constant in `Constants.bas`: `Public Const HDR_JOIN_DATE As String = "Join Date"`
2. Re-run the import — the column is picked up automatically.

## Editing and Re-importing Modules

To apply changes back to the workbook:
1. Open `FaithWorksPlanningMaster_2026.xlsm`
2. Open the VBA editor (Alt+F11)
3. Right-click the target module → Remove, then File → Import to bring in the updated `.bas` or `.frm` file
4. Run **Debug → Compile VBAProject** to verify no errors
