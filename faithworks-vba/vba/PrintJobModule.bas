Option Explicit

'===============================================================================
' PrintJobModule.bas
' Author: Steve Lashinski, 2026
' Given a job number, prints all participants assigned to that job.
'
' Print layout:
'   Row 1      : Job number -- large, bold, centered across A:B
'   Rows 2-3   : Blank spacer
'   Rows 4+    : Last (col A, left)  |  First (col B, left)
'   Col widths : A=22, B=18 -- equal feel, centered as block via PageSetup
'===============================================================================

Public Sub PrintJob(ByVal jobToPrint As String)

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False

    ' -- 1. Resolve columns ------------------------------------------------------
    Dim colFirst As Long, colLast As Long
    If Not SharedPrintHelpers.RequireColumn(HDR_FIRST, colFirst) Then GoTo Cleanup
    If Not SharedPrintHelpers.RequireColumn(HDR_LAST, colLast) Then GoTo Cleanup

    Dim dayCols(1 To 5) As Long
    dayCols(1) = ImportModule.GetMappedColumn(HDR_JOB_MON)
    dayCols(2) = ImportModule.GetMappedColumn(HDR_JOB_TUE)
    dayCols(3) = ImportModule.GetMappedColumn(HDR_JOB_WED)
    dayCols(4) = ImportModule.GetMappedColumn(HDR_JOB_THU)
    dayCols(5) = ImportModule.GetMappedColumn(HDR_JOB_FRI)

    ' -- 2. Get participant sheet -------------------------------------------------
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

    ' -- 3. Read all data into array ---------------------------------------------
    Dim dataArr As Variant
    dataArr = participantsWs.Range("A3", participantsWs.Cells(lastRow, lastCol)).Value

    ' -- 4. Create temp sheet and collect matching rows --------------------------
    Dim tempWs As Worksheet
    Set tempWs = SharedPrintHelpers.GetTempSheet()
    If tempWs Is Nothing Then GoTo Cleanup

    ' Force text on both name columns before writing anything
    tempWs.Columns("A").NumberFormat = "@"
    tempWs.Columns("B").NumberFormat = "@"

    Dim tempRow As Long
    tempRow = 4   ' rows 1-3 reserved for header

    Dim r As Long, d As Long
    For r = 2 To UBound(dataArr, 1)
        For d = 1 To 5
            If dayCols(d) > 0 Then
                If Trim(CStr(dataArr(r, dayCols(d)))) = Trim(jobToPrint) Then
                    tempWs.Cells(tempRow, 1).Value = CStr(dataArr(r, colLast))
                    tempWs.Cells(tempRow, 2).Value = CStr(dataArr(r, colFirst))
                    tempRow = tempRow + 1
                    Exit For
                End If
            End If
        Next d
    Next r

    If tempRow = 4 Then
        MsgBox "No participants found for job: " & jobToPrint, _
               vbInformation, "FaithWorks Print"
        GoTo Cleanup
    End If

    ' Deduplicate on Last + First
    tempWs.Range("A4", tempWs.Cells(tempRow - 1, 2)).RemoveDuplicates Columns:=Array(1, 2)

    ' -- 5. Format ---------------------------------------------------------------
    Dim lastTempRow As Long
    lastTempRow = tempWs.Cells(tempWs.Rows.Count, "A").End(xlUp).Row

    ' Job number header: merged A1:B1, large, centered, text-forced
    tempWs.Range("A1").NumberFormat = "@"
    With tempWs.Range("A1:B1")
        .Merge
        .Value = jobToPrint
        .Font.Name = FW_FONT_NAME
        .Font.Size = PRINT_FONT_HEADER
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
    End With

    ' Name rows
    If lastTempRow >= 4 Then
        With tempWs.Range("A4:A" & lastTempRow)
            .Font.Name = FW_FONT_NAME
            .Font.Size = PRINT_FONT_JOB_HDR
            .Font.Bold = False
            .HorizontalAlignment = xlLeft
        End With
        With tempWs.Range("B4:B" & lastTempRow)
            .Font.Name = FW_FONT_NAME
            .Font.Size = PRINT_FONT_JOB_HDR
            .Font.Bold = False
            .HorizontalAlignment = xlLeft
        End With
    End If

    ' Fixed column widths -- Last wider than First, block centered by PageSetup
    tempWs.Columns("A").ColumnWidth = COL_WIDTH_LAST
    tempWs.Columns("B").ColumnWidth = COL_WIDTH_FIRST

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

    ' -- 6. Preview then clean up ------------------------------------------------
    SharedPrintHelpers.PrintPreviewAndCleanup tempWs, xlPortrait
    Set tempWs = Nothing

    participantsWs.Activate
    GoTo Cleanup

ErrHandler:
    MsgBox "Error in PrintJob: " & Err.Description, vbExclamation, "FaithWorks Print"

Cleanup:
    If Not tempWs Is Nothing Then
        Application.DisplayAlerts = False
        On Error Resume Next
        tempWs.Delete
        On Error GoTo 0
        Application.DisplayAlerts = True
    End If
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True

End Sub
