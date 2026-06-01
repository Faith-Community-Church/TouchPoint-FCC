Option Explicit

' =============================================================================
' StyleModule -- FaithWorksPlanningMaster 2026
' Applies all styling to FwParticipants after import.
' Called by ImportModule step 11.
'
' Sheet layout:
'   Rows 1-2  : Plain white background. Buttons float here as shapes.
'               NEVER formatted here -- SetShapes owns the buttons.
'   Row 3     : ListObject header row with AutoFilter
'   Rows 4+   : Participant data
'   Cols A-?  : Dynamic -- 19 core columns + Request + Job-Mon..Job-Fri
'
' All column ranges use lastCol (dynamic) not a hardcoded 19.
' =============================================================================

Public Sub ApplyFwParticipantsStyle()
    Dim ws As Worksheet
    Set ws = SharedPrintHelpers.GetParticipantSheet()

    ApplyTableStyle ws
    ApplyFontAndFill ws
    ApplyBorders ws
    ApplyRowHeights ws
    ApplyColumnWidths ws
    ClearScrollArea ws
    FreezeAtC4 ws
End Sub

'
