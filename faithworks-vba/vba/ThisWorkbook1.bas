'===============================================================================
' ThisWorkbook.cls
' Double-click any cell in the Mon-Fri columns on FwParticipants to toggle
' a colour highlight. Double-click again to clear it.
' Column positions are resolved dynamically via GetMappedColumn so this works
' regardless of column order after any import.
'===============================================================================

Option Explicit



Private Sub Workbook_SheetBeforeDoubleClick( _
        ByVal Sh As Object, _
        ByVal Target As Range, _
        Cancel As Boolean)

    On Error GoTo ErrHandler

    ' Only act on the participant sheet
    Dim participantSheetName As String
    participantSheetName = ThisWorkbook.Sheets(PARAM_SHEET) _
                               .Range(PARAM_PARTICIPANT_WS).Value

    If Sh.Name <> participantSheetName Then Exit Sub

    Dim lastRow As Long
    lastRow = Sh.Cells(Sh.Rows.Count, "A").End(xlUp).Row

    ' Resolve weekday column indices
    Dim colMon As Long, colTue As Long, colWed As Long
    Dim colThu As Long, colFri As Long
    colMon = ImportModule.GetMappedColumn(HDR_MON)
    colTue = ImportModule.GetMappedColumn(HDR_TUE)
    colWed = ImportModule.GetMappedColumn(HDR_WED)
    colThu = ImportModule.GetMappedColumn(HDR_THU)
    colFri = ImportModule.GetMappedColumn(HDR_FRI)

    ' Build the watchable range from the resolved columns
    Dim watchRng As Range
    Dim colIdx As Variant
    For Each colIdx In Array(colMon, colTue, colWed, colThu, colFri)
        If CLng(colIdx) > 0 Then
            Dim oneCol As Range
            Set oneCol = Sh.Range(Sh.Cells(2, CLng(colIdx)), Sh.Cells(lastRow, CLng(colIdx)))
            If watchRng Is Nothing Then
                Set watchRng = oneCol
            Else
                Set watchRng = Union(watchRng, oneCol)
            End If
        End If
    Next colIdx

    If watchRng Is Nothing Then Exit Sub
    If Intersect(Target, watchRng) Is Nothing Then Exit Sub

    Cancel = True   ' suppress Excel entering cell-edit mode on double-click

    ' Determine which colour to apply based on which day was clicked
    Dim targetCol As Long
    targetCol = Target.Column

    Dim highlightColor As Integer
    If targetCol = colMon Then highlightColor = COLOR_MON
    ElseIf targetCol = colTue Then highlightColor = COLOR_TUE
    ElseIf targetCol = colWed Then highlightColor = COLOR_WED
    ElseIf targetCol = colThu Then highlightColor = COLOR_THU
    ElseIf targetCol = colFri Then highlightColor = COLOR_FRI
    Else
        Exit Sub
    End If

    With Target
        If .Interior.ColorIndex = xlNone Then
            .Interior.ColorIndex = highlightColor
            .Font.ColorIndex = COLOR_TEXT_ON
            .Borders.ColorIndex = 1
        Else
            .Interior.ColorIndex = xlNone
            .Font.ColorIndex = COLOR_TEXT_OFF
            .Borders.ColorIndex = xlNone
        End If
    End With

    Exit Sub

ErrHandler:
    ' Swallow errors silently in event handlers â€” if the import has not been
    ' run yet, GetMappedColumn returns 0 and we simply do nothing.

End Sub
