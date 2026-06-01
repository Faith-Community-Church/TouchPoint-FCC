Option Explicit

'===============================================================================
' PrintParticipantsJobDayModule.bas
' For a selected weekday, prints ALL participants with a job assignment that day.
' Sorted by Last name. Three aligned columns: Last | First | Job number.
'
' Print layout:
'   Row 1      : Day name -- large, bold, centered across A:C
'   Rows 2-3   : Blank spacer
'   Rows 4+    : Last (col A)  |  First (col B)  |  Job# (col C)
'   Col widths : A=22, B=18, C=10
'===============================================================================

Public Sub PrintParticipantsJobDay(ByVal dayToPrint As String)

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    ' -- 1. Resolve the Job column for the selected day --------------------------
    Dim jobColIdx As Long
    jobColIdx = ImportModule.GetMappedColumn("Job-" & dayToPrint)
    If jobColIdx = 0 Then
        MsgBox "Column 'Job-" & dayToPrint & "' not found." & vbCr & _
               "Please re-run the import and try again.", _
               vbExclamation, "FaithWorks Print"
        GoTo Cleanup
    End If

    ' -- 2. Resolve name columns -------------------------------------------------
    Dim colFirst As Long, colLast As Long
    If Not SharedPrintHelpers.RequireColumn(HDR_FIRST, colFirst) Then GoTo Cleanup
    If Not SharedPrintHelpers.RequireColumn(HDR_LAST, colLast) Then GoTo Cleanup

    ' -- 3. Get participant sheet -------------------------------------------------
    Dim participantsWs As Worksheet
    Set participantsWs = SharedPrintHelpers.GetParticipantSheet()
    If participantsWs Is Nothing Then GoTo Cleanup

    Dim lastRow As Long
    lastRow = participantsWs.Cells(participantsWs.Rows.Count, "D").End(xlUp).Row
    If lastRow < 4 Then
        MsgBox "The participant sheet is empty.", vbInformation, "FaithWorks Print"
        GoTo Cleanup
    End If

    Dim lastCol As Long
    lastCol = participantsWs.Cells(3, participantsWs.Columns.Count).End(xlToLeft).Column

    Dim dataArr As Variant
    dataArr = participantsWs.Range("A3", participantsWs.Cells(lastRow, lastCol)).Value

    ' -- 4. Build temp sheet -----------------------------------------------------
    Dim tempWs As Worksheet
    Set tempWs = SharedPrintHelpers.GetTempSheet()
    If tempWs Is Nothing Then GoTo Cleanup

    ' Force text on all three columns before writing anything
    tempWs.Columns("A").NumberFormat = "@"
    tempWs.Columns("B").NumberFormat = "@"
    tempWs.Columns("C").NumberFormat = "@"

    ' -- 5. Day header: merged A1:C1, large, centered ----------------------------
    With tempWs.Range("A1:C1")
        .Merge
        .Value = dayToPrint
        .Font.Name = FW_FONT_NAME
        .Font.Size = PRINT_FONT_HEADER
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
    End With

    ' -- 6. Write participant rows ------------------------------------------------
    Dim writeRow As Long
    writeRow = 4

    Dim rr As Long
    For rr = 2 To UBound(dataArr, 1)
        Dim jobAssignment As String
        jobAssignment = Trim(CStr(dataArr(rr, jobColIdx)))
        If jobAssignment <> "" Then
            tempWs.Cells(writeRow, 1).Value = CStr(dataArr(rr, colLast))
            tempWs.Cells(writeRow, 2).Value = CStr(dataArr(rr, colFirst))
            tempWs.Cells(writeRow, 3).Value = jobAssignment
            writeRow = writeRow + 1
        End If
    Next rr

    If writeRow = 4 Then
        MsgBox "No participants with job assignments found for " & dayToPrint & ".", _
               vbInformation, "FaithWorks Print"
        GoTo Cleanup
    End If

    ' -- 7. Format name rows -----------------------------------------------------
    With tempWs.Range("A4:A" & (writeRow - 1))
        .Font.Name = FW_FONT_NAME
        .Font.Size = PRINT_FONT_BODY
        .Font.Bold = False
        .HorizontalAlignment = xlLeft
    End With
    With tempWs.Range("B4:B" & (writeRow - 1))
        .Font.Name = FW_FONT_NAME
        .Font.Size = PRINT_FONT_BODY
        .Font.Bold = False
        .HorizontalAlignment = xlLeft
    End With
    With tempWs.Range("C4:C" & (writeRow - 1))
        .Font.Name = FW_FONT_NAME
        .Font.Size = PRINT_FONT_BODY
        .Font.Bold = False
        .HorizontalAlignment = xlLeft
    End With

    ' Fixed column widths -- consistent with other print modules
    tempWs.Columns("A").ColumnWidth = COL_WIDTH_LAST
    tempWs.Columns("B").ColumnWidth = COL_WIDTH_FIRST
    tempWs.Columns("C").ColumnWidth = COL_WIDTH_JOB

    With tempWs.PageSetup
        .orientation = xlPortrait
        .CenterHorizontally = True
        .CenterVertically = False
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = 99
        .LeftMargin = Application.InchesToPoints(0.75)
        .RightMargin = Application.InchesToPoints(0.75)
        .TopMargin = Application.InchesToPoints(0.75)
        .BottomMargin = Application.InchesToPoints(0.75)
        .CenterHeader = ""
        .LeftHeader = ""
        .RightHeader = ""
    End With

    ' -- 8. Preview and clean up -------------------------------------------------
    SharedPrintHelpers.PrintPreviewAndCleanup tempWs, xlPortrait
    Set tempWs = Nothing

    participantsWs.Activate
    GoTo Cleanup

ErrHandler:
    MsgBox "Error in PrintParticipantsJobDay: " & Err.Description, _
           vbExclamation, "FaithWorks Print"

Cleanup:
    If Not tempWs Is Nothing Then
        Application.DisplayAlerts = False
        On Error Resume Next
        tempWs.Delete
        On Error GoTo 0
        Application.DisplayAlerts = True
    End If
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True

End Sub
