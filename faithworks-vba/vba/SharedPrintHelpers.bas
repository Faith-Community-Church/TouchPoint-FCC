Option Explicit

'===============================================================================
' SharedPrintHelpers.bas
' Author: Steve Lashinski, 2026
' Shared utility routines used by all print modules.
' Non-developer note: Think of this as a shared tool drawer â€” instead of each
' module carrying its own copy of the same tools, they all use these.
'===============================================================================


'===============================================================================
' GetParticipantSheet
' Reads ParticipantSheetName from Parameters and returns that worksheet.
' Returns Nothing and shows an error if the sheet cannot be found.
'===============================================================================
Public Function GetParticipantSheet() As Worksheet

    On Error GoTo ErrHandler

    Dim sheetName As String
    sheetName = ThisWorkbook.Sheets(PARAM_SHEET).Range(PARAM_PARTICIPANT_WS).Value
    If sheetName = "" Then sheetName = "FwParticipants"

    Set GetParticipantSheet = ThisWorkbook.Sheets(sheetName)
    Exit Function

ErrHandler:
    MsgBox "Could not find the participant sheet named '" & sheetName & "'." & vbCr & _
           "Check the ParticipantSheetName value on the Parameters sheet.", _
           vbExclamation, "FaithWorks"
    Set GetParticipantSheet = Nothing

End Function


'===============================================================================
' GetTempSheet
' Creates a fresh temporary worksheet for assembling print layouts.
' Deletes any leftover temp sheet from a previous crashed run.
' Caller must delete the sheet when done (or call PrintPreviewAndCleanup).
'===============================================================================
Public Function GetTempSheet() As Worksheet

    On Error GoTo ErrHandler

    Dim tempName As String
    tempName = ThisWorkbook.Sheets(PARAM_SHEET).Range(PARAM_TEMP_SHEET).Value
    If tempName = "" Then tempName = "FW_Temp_Print"

    ' Remove any leftover from a previous crashed run
    Dim oldWs As Worksheet
    On Error Resume Next
    Set oldWs = ThisWorkbook.Sheets(tempName)
    On Error GoTo ErrHandler
    If Not oldWs Is Nothing Then
        Application.DisplayAlerts = False
        oldWs.Delete
        Application.DisplayAlerts = True
    End If

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets.Add( _
        After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    ws.Name = tempName

    Set GetTempSheet = ws
    Exit Function

ErrHandler:
    MsgBox "Could not create the temporary print sheet." & vbCr & _
           "Error: " & Err.Description, vbExclamation, "FaithWorks Print"
    Set GetTempSheet = Nothing

End Function


'===============================================================================
' RequireColumn
' Convenience wrapper around GetMappedColumn.
' Fills colIdx and returns True if the column was found.
' Shows a clear error and returns False if not found â€” caller should Exit Sub.
'
' Usage:
'   Dim colFirst As Long
'   If Not RequireColumn(HDR_FIRST, colFirst) Then Exit Sub
'===============================================================================
Public Function RequireColumn(ByVal headerName As String, _
                               ByRef colIdx As Long) As Boolean

    colIdx = ImportModule.GetMappedColumn(headerName)

    If colIdx = 0 Then
        MsgBox "Column '" & headerName & "' was not found in the participant sheet." & vbCr & vbCr & _
               "This usually means the import has not been run yet, or the TouchPoint " & _
               "export is missing that column." & vbCr & vbCr & _
               "Please re-run the import and try again.", _
               vbExclamation, "FaithWorks â€” Missing Column"
        RequireColumn = False
    Else
        RequireColumn = True
    End If

End Function


'===============================================================================
' PrintPreviewAndCleanup
' Sets page orientation, shows the print preview, then deletes the temp sheet.
'===============================================================================
Public Sub PrintPreviewAndCleanup(ByRef printWs As Worksheet, _
                                   ByVal orientation As XlPageOrientation)

    On Error GoTo ErrHandler

    printWs.PageSetup.orientation = orientation
    Application.ScreenUpdating = True
    printWs.PrintPreview
    Application.ScreenUpdating = False

    Application.DisplayAlerts = False
    printWs.Delete
    Application.DisplayAlerts = True
    Exit Sub

ErrHandler:
    MsgBox "Error during print preview: " & Err.Description, _
           vbExclamation, "FaithWorks Print"
    On Error Resume Next
    Application.DisplayAlerts = False
    printWs.Delete
    Application.DisplayAlerts = True

End Sub
