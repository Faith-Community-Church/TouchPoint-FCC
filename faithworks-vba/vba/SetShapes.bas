Option Explicit

'===============================================================================
' SetShapes.bas
' Author: Steve Lashinski, 2026
' Creates the navy header band (rows 1-2) and two shape buttons.
'===============================================================================
'
' Sheet layout contract:
'   Rows 1-2 : Navy header band, RGB(31,56,100). NEVER cleared by other modules.
'   Row 3    : ListObject header / AutoFilter.
'   Rows 4+  : Participant data.
'   Cols A-S : 19 columns.
'
' Guard strategy:
'   Rows 1-2 are considered "already initialised" when A1.Interior.Color
'   equals the navy constant. Any other state (including xlColorIndexNone)
'   means the band is absent and must be inserted.
'
' Button strategy:
'   Buttons are identified by Name, not index. On every call we delete any
'   existing shape whose name matches a known button name, then re-create it
'   fresh. This makes the routine idempotent across import/re-import cycles.

'
