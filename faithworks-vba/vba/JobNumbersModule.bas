Option Explicit

'===============================================================================
' JobNumbersModule.bas
' Author: Steve Lashinski, 2026
' Builds a sorted, deduplicated list of all job numbers found across the five
' Job-Mon through Job-Fri columns on the FwParticipants sheet.
' Used by JobListBox.UserForm_Initialize to populate the job-number combo box.
'
' Note: scans HDR_JOB_MON..HDR_JOB_FRI (the assignment columns, e.g. "14-4"),
' NOT HDR_MON..HDR_FRI (the availability/day columns, e.g. "Yes").
'===============================================================================

Public Function CreateUniqueJobNumberList() As Collection

    On Error GoTo ErrHandler

    ' -- Get the participant sheet -----------------------------------------------
    Dim participantsWs As Worksheet
    Set participantsWs = SharedPrintHelpers.GetParticipantSheet()
    If participantsWs Is Nothing Then
        Set CreateUniqueJobNumberList = New Collection
        Exit Function
    End If

    ' -- Resolve Job column indices via GetMappedColumn --------------------------
    ' Returns 0 for any column not present -- those are simply skipped below.
    Dim dayCols(1 To 5) As Long
    dayCols(1) = ImportModule.GetMappedColumn(HDR_JOB_MON)
    dayCols(2) = ImportModule.GetMappedColumn(HDR_JOB_TUE)
    dayCols(3) = ImportModule.GetMappedColumn(HDR_JOB_WED)
    dayCols(4) = ImportModule.GetMappedColumn(HDR_JOB_THU)
    dayCols(5) = ImportModule.GetMappedColumn(HDR_JOB_FRI)

    ' Use UsedRange for lastRow -- reliable even when column A has blanks
    Dim lastRow As Long
    lastRow = participantsWs.UsedRange.Row + participantsWs.UsedRange.Rows.Count - 1

    If lastRow < 4 Then
        Set CreateUniqueJobNumberList = New Collection
        Exit Function
    End If

    ' -- Read all five Job columns, accumulate unique values ---------------------
    ' Reading each column as a Variant array avoids cell-by-cell worksheet
    ' access, which is significantly faster on large sheets.
    Dim allJobs As New Collection
    Dim d As Long

    For d = 1 To 5
        If dayCols(d) > 0 Then
            Dim dayArr As Variant
            dayArr = participantsWs.Range( _
                         participantsWs.Cells(4, dayCols(d)), _
                         participantsWs.Cells(lastRow, dayCols(d))).Value

            Dim r As Long
            For r = 1 To UBound(dayArr, 1)
                Dim cellVal As String
                cellVal = Trim(CStr(dayArr(r, 1)))
                If cellVal <> "" Then
                    On Error Resume Next
                    allJobs.Add Item:=cellVal, key:=cellVal
                    On Error GoTo ErrHandler
                End If
            Next r
        End If
    Next d

    Set CreateUniqueJobNumberList = SortCollection(allJobs)
    Exit Function

ErrHandler:
    MsgBox "Error building job number list: " & Err.Description, _
           vbExclamation, "FaithWorks"
    Set CreateUniqueJobNumberList = New Collection

End Function
