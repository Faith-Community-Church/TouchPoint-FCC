Option Explicit

'===============================================================================
' JobDayClass.bas
' Author: Steve Lashinski, 2026
' Encapsulates day-specific column information for the print modules.
' Call Initialise("Mon") etc. before reading any properties.
'
' Non-developer note: this "class" acts like a lookup card for a single weekday.
' You create one, tell it which day you want, and it tells you which column
' that day lives in â€” without any hardcoded column letters anywhere.
'===============================================================================

Private pJobDay    As String
Private pColIdx    As Long    ' 1-based column index on FwParticipants

'===============================================================================
' Initialise
' Looks up the column index for the given day via GetMappedColumn.
' dayOfJob should be "Mon", "Tue", "Wed", "Thu", or "Fri".
'===============================================================================
Public Sub Initialise(ByVal dayOfJob As String)

    pJobDay = Trim(dayOfJob)

    Dim canonicalHeader As String
    Select Case UCase(pJobDay)
        Case "MON": canonicalHeader = HDR_MON
        Case "TUE": canonicalHeader = HDR_TUE
        Case "WED": canonicalHeader = HDR_WED
        Case "THU": canonicalHeader = HDR_THU    ' resolves "Thurs" alias -> col 12
        Case "FRI": canonicalHeader = HDR_FRI
        Case Else
            pJobDay = "All"
            pColIdx = 0
            Exit Sub
    End Select

    pColIdx = ImportModule.GetMappedColumn(canonicalHeader)

End Sub

' â”€â”€ Read-only properties â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

' The day label, e.g. "Mon"
Public Property Get JobDay() As String
    JobDay = pJobDay
End Property

' 1-based column index. Returns 0 if Initialise was not called or
' the column was not found (import has not been run).
Public Property Get JobDayColIdx() As Long
    JobDayColIdx = pColIdx
End Property

' AutoFilter Field number â€” same as JobDayColIdx when filtering from column A.
Public Property Get AutoFilterField() As Long
    AutoFilterField = pColIdx
End Property

' Column letter string for backward-compatible code that still expects "R" etc.
' New code should use JobDayColIdx directly.
Public Property Get JobdayColumn() As String
    If pColIdx > 0 Then
        JobdayColumn = Split(Cells(1, pColIdx).Address(True, True), "$")(1)
    Else
        JobdayColumn = ""
    End If
End Property

' Numeric string of the AutoFilter field â€” kept for any remaining legacy callers.
Public Property Get JobDayFilterField() As String
    JobDayFilterField = CStr(pColIdx)
End Property
