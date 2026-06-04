Option Explicit

'===============================================================================
' PrintJobDayModule.bas
' Author: Steve Lashinski, 2026
' For a selected weekday, prints one section per job number found that day.
' Each section: large job header, then Last / First in two aligned columns.
'
' Print layout per section:
'   Row N      : "Mon 12-8" -- large, bold, centered across A:B
'   Rows N+1-2 : Blank spacer
'   Rows N+3+  : Last (col A, left)  |  First (col B, left)
'   Page break after each section
'   Col widths : A=22, B=18
'===============================================================================

Public Sub PrintJobDay(ByVal dayToPrint As String)

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

    ' -- 4. Collect unique job numbers for this day, sorted ----------------------
    Dim uniqueJobs As New Collection
    Dim rr As Long
    For rr = 2 To UBound(dataArr, 1)
        Dim jobVal As String
        jobVal = Trim(CStr(dataArr(rr, jobColIdx)))
        If jobVal <> "" Then
            On Error Resume Next
            uniqueJobs.Add Item:=jobVal, key:=jobVal
            On Error GoTo ErrHandler
        End If
    Next rr

    If uniqueJobs.Count = 0 Then
        MsgBox "No job assignments found for " & dayToPrint & ".", _
               vbInformation, "FaithWorks Print"
        GoTo Cleanup
    End If

    Set uniqueJobs = SortCollection(uniqueJobs)

    ' -- 5. Build temp sheet -----------------------------------------------------
    Dim tempWs As Worksheet
    Set tempWs = SharedPrintHelpers.GetTempSheet()
    If tempWs Is Nothing Then GoTo Cleanup

    ' Force text on both columns before writing anything
    tempWs.Columns("A").NumberFormat = "@"
    tempWs.Columns("B").NumberFormat = "@"
    tempWs.Columns("A").ColumnWidth = COL_WIDTH_LAST
    tempWs.Columns("B").ColumnWidth = COL_WIDTH_FIRST

    tempWs.ResetAllPageBreaks

    Dim printRow As Long
    printRow = 1

    Dim jobItem As Variant
    For Each jobItem In uniqueJobs

        ' Collect participants for this job
        Dim names() As String
        ReDim names(1 To (lastRow - 3), 1 To 2)
        Dim nameCount As Long
        nameCount = 0

        For rr = 2 To UBound(dataArr, 1)
            If Trim(CStr(dataArr(rr, jobColIdx))) = CStr(jobItem) Then
                nameCount = nameCount + 1
                names(nameCount, 1) = CStr(dataArr(rr, colLast))
                names(nameCount, 2) = CStr(dataArr(rr, colFirst))
            End If
        Next rr

        If nameCount > 0 Then
            ' Section header: "Mon 12-8" merged across A:B, large, centered
            tempWs.Cells(printRow, 1).NumberFormat = "@"
            With tempWs.Range( _
                    tempWs.Cells(printRow, 1), tempWs.Cells(printRow, 2))
                .Merge
                .Value = dayToPrint & " " & CStr(jobItem)
                .Font.Name = FW_FONT_NAME
                .Font.Size = PRINT_FONT_HEADER
                .Font.Bold = True
                .HorizontalAlignment = xlCenter
            End With

            ' Name rows starting 3 rows below header
            Dim dataStartRow As Long
            dataStartRow = printRow + 3
            Dim pr As Long
            For pr = 1 To nameCount
                tempWs.Cells(dataStartRow + pr - 1, 1).Value = names(pr, 1)
                tempWs.Cells(dataStartRow + pr - 1, 2).Value = names(pr, 2)
            Next pr

            ' Format name rows
            With tempWs.Range("A" & dataStartRow & ":A" & (dataStartRow + nameCount - 1))
                .Font.Name = FW_FONT_NAME
                .Font.Size = PRINT_FONT_JOB_HDR
                .Font.Bold = False
                .HorizontalAlignment = xlLeft
            End With
            With tempWs.Range("B" & dataStartRow & ":B" & (dataStartRow + nameCount - 1))
                .Font.Name = FW_FONT_NAME
                .Font.Size = PRINT_FONT_JOB_HDR
                .Font.Bold = False
                .HorizontalAlignment = xlLeft
            End With

            ' Page break after section
            Dim breakRow As Long
            breakRow = dataStartRow + nameCount + 1
            tempWs.Rows(breakRow).PageBreak = xlPageBreakManual

            printRow = breakRow + 2
        End If

    Next jobItem

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

    ' -- 6. Preview and clean up -------------------------------------------------
    SharedPrintHelpers.PrintPreviewAndCleanup tempWs, xlPortrait
    Set tempWs = Nothing

    participantsWs.Activate
    GoTo Cleanup

ErrHandler:
    MsgBox "Error in PrintJobDay: " & Err.Description, vbExclamation, "FaithWorks Print"

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
