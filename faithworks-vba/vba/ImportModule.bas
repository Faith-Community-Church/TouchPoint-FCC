Option Explicit

'===============================================================================
' ImportModule.bas
' Updated: May 2026
'
' WHAT THIS MODULE DOES:
'   1. Shows a browse dialog so the user picks the saved TouchPoint .xlsx export
'   2. Opens that file silently (read-only)
'   3. Copies all data into the FwParticipants sheet in this workbook
'   4. Sorts by Last name then First name
'   5. Applies Times New Roman Bold font and FW Table Style table formatting
'   6. Freezes rows 1-3 and columns A-B (header band + headers stay visible)
'   7. Builds a dynamic header map so every other module can look up columns
'      by name instead of hardcoded letters -- stored at Parameters rows 200-260
'
' COLUMN HEADER REFERENCE (from 2026 TouchPoint export):
'   Col  1  Minor or Adult
'   Col  2  Registration OrganizationId
'   Col  3  First
'   Col  4  Last
'   Col  5  Goes By        (alias: GoesBy)
'   Col  6  Age
'   Col  7  CellPhone      (alias: Phone)
'   Col  8  Email          (alias: EmailAddress)
'   Col  9  Mon
'   Col 10  Tue
'   Col 11  Wed
'   Col 12  Thu            (alias: Thurs)
'   Col 13  Fri
'   Col 14  Pro Skill      (alias: ProSkill)
'   Col 15  Licensed
'   Col 16  Int Skill      (alias: IntSkill)
'   Col 17  Nov Skill      (alias: NovSkill)
'   Col 18  MC
'   Col 19  MC Project     (alias: MCP)
'   Col 20  Request
'   Col 21  Job-Mon
'   Col 22  Job-Tue
'   Col 23  Job-Wed
'   Col 24  Job-Thu
'   Col 25  Job-Fri
'===============================================================================


'===============================================================================
' FaithWorksImport, MAIN ENTRY POINT
' Called by the Import button on the FwParticipants sheet.
'===============================================================================
Public Sub FaithWorksImport()

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    '
