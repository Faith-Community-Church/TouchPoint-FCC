Option Explicit

'===============================================================================
' TestModule.bas
' Author: Steve Lashinski, 2026
' Manual unit tests. Run any individual sub with F5, or run RunAllTests()
' to execute the full suite. No live TouchPoint export or Word needed.
' Tests write temporary data and always clean up after themselves.
'===============================================================================

Private mPassCount    As Long
Private mFailCount    As Long
Private mFailMessages As String

' ============================================================
' RunAllTests -- master runner
' ============================================================
Public Sub RunAllTests()
    mPassCount = 0
    mFailCount = 0
    mFailMessages = ""

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    Test_GetMappedColumn_ReturnsCorrectIndex
    Test_GetMappedColumn_CaseInsensitive
    Test_GetMappedColumn_AliasResolution
    Test_GetMappedColumn_MissingColumnReturnsZero
    Test_GetMappedColumn_EmptySheet
    Test_GetMappedColumn_DuplicateHeaderUsesFirst
    Test_SortCollection_BasicOrder
    Test_SortCollection_SingleItem
    Test_SortCollection_EmptyCollection
    Test_CreateUniqueJobNumberList_DeduplicatesAcrossDays
    Test_CreateUniqueJobNumberList_EmptySheet

    Application.ScreenUpdating = True
    Application.DisplayAlerts = True

    Dim summary As String
    summary = "Test Results:" & vbCr & vbCr & _
              "  PASS: " & mPassCount & vbCr & _
              "  FAIL: " & mFailCount

    If mFailCount > 0 Then
        summary = summary & vbCr & vbCr & "Failures:" & vbCr & mFailMessages
        MsgBox summary, vbExclamation, "FaithWorks Tests"
    Else
        MsgBox summary, vbInformation, "FaithWorks Tests -- All Passed"
    End If
End Sub

' ============================================================
' Assertion helpers
' ============================================================
Private Sub AssertEqual(ByVal testName As String, _
                        ByVal expected As Variant, _
                        ByVal actual As Variant)
    If CStr(expected) = CStr(actual) Then
        mPassCount = mPassCount + 1
    Else
        mFailCount = mFailCount + 1
        mFailMessages = mFailMessages & "  [FAIL] " & testName & vbCr & _
                        "         Expected: " & CStr(expected) & vbCr & _
                        "         Got:      " & CStr(actual) & vbCr
    End If
End Sub

Private Sub AssertTrue(ByVal testName As String, ByVal condition As Boolean)
    AssertEqual testName, True, condition
End Sub

' ============================================================
' Mock helpers
' ============================================================

' Writes a fake header map to Parameters rows 200-260 so GetMappedColumn
' can be tested without running a real import.
' Headers: TouchPoint cols 1-21 (Join Date/Time at 9-10), then Request(22),
'          Job-Mon..Job-Fri(23-27). Plus canonical aliases.
Private Sub MockHeaderMap()
    Dim p As Worksheet
    Set p = ThisWorkbook.Sheets(PARAM_SHEET)
    p.Range(p.Cells(200, 1), p.Cells(260, 2)).ClearContents
    p.Cells(200, 1).Value = "ColMapKey"
    p.Cells(200, 2).Value = "ColIndex"

    Dim hdrs As Variant
    hdrs = Array("Minor or Adult", "Registration OrganizationId", "First", "Last", _
                 "Goes By", "Age", "CellPhone", "Email", "Join Date", "Join Time", _
                 "Mon", "Tue", "Wed", "Thu", "Fri", "Pro Skill", "Licensed", _
                 "Int Skill", "Nov Skill", "MC", "MC Project", "Request", _
                 "Job-Mon", "Job-Tue", "Job-Wed", "Job-Thu", "Job-Fri")

    Dim i As Long
    For i = 0 To UBound(hdrs)
        p.Cells(201 + i, 1).Value = hdrs(i)
        p.Cells(201 + i, 2).Value = i + 1
    Next i

    Dim base As Long
    base = 201 + UBound(hdrs) + 1
    ' Aliases
    p.Cells(base, 1).Value = "GoesBy":        p.Cells(base, 2).Value = 5
    p.Cells(base + 1, 1).Value = "Phone":     p.Cells(base + 1, 2).Value = 7
    p.Cells(base + 2, 1).Value = "Thurs":     p.Cells(base + 2, 2).Value = 14
    p.Cells(base + 3, 1).Value = "ProSkill":  p.Cells(base + 3, 2).Value = 16
    p.Cells(base + 4, 1).Value = "IntSkill":  p.Cells(base + 4, 2).Value = 18
    p.Cells(base + 5, 1).Value = "NovSkill":  p.Cells(base + 5, 2).Value = 19
    p.Cells(base + 6, 1).Value = "MCP":       p.Cells(base + 6, 2).Value = 21
End Sub

Private Sub CleanMockHeaderMap()
    Dim p As Worksheet
    Set p = ThisWorkbook.Sheets(PARAM_SHEET)
    p.Range(p.Cells(200, 1), p.Cells(260, 2)).ClearContents
End Sub

Private Function MockParticipantSheet() As Worksheet
    Const TEST_SHEET As String = "FW_Test_Participants"
    Dim oldWs As Worksheet
    On Error Resume Next
    Set oldWs = ThisWorkbook.Sheets(TEST_SHEET)
    On Error GoTo 0
    If Not oldWs Is Nothing Then
        Application.DisplayAlerts = False
        oldWs.Delete
        Application.DisplayAlerts = True
    End If
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets.Add( _
        After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    ws.Name = TEST_SHEET
    ThisWorkbook.Sheets(PARAM_SHEET).Range(PARAM_PARTICIPANT_WS).Value = TEST_SHEET
    Set MockParticipantSheet = ws
End Function

Private Sub CleanMockParticipantSheet()
    Const TEST_SHEET As String = "FW_Test_Participants"
    Application.DisplayAlerts = False
    On Error Resume Next
    ThisWorkbook.Sheets(TEST_SHEET).Delete
    On Error GoTo 0
    Application.DisplayAlerts = True
    ThisWorkbook.Sheets(PARAM_SHEET).Range(PARAM_PARTICIPANT_WS).Value = "FwParticipants"
End Sub

' ============================================================
' Tests: GetMappedColumn
' ============================================================
Public Sub Test_GetMappedColumn_ReturnsCorrectIndex()
    MockHeaderMap
    AssertEqual "First=3", 3, ImportModule.GetMappedColumn("First")
    AssertEqual "Last=4", 4, ImportModule.GetMappedColumn("Last")
    AssertEqual "Join Date=9", 9, ImportModule.GetMappedColumn(HDR_JOIN_DATE)
    AssertEqual "Mon=11", 11, ImportModule.GetMappedColumn("Mon")
    AssertEqual "Thu=14", 14, ImportModule.GetMappedColumn("Thu")
    AssertEqual "MC Project=21", 21, ImportModule.GetMappedColumn("MC Project")
    CleanMockHeaderMap
End Sub

Public Sub Test_GetMappedColumn_CaseInsensitive()
    MockHeaderMap
    AssertEqual "FIRST upper", 3, ImportModule.GetMappedColumn("FIRST")
    AssertEqual "first lower", 3, ImportModule.GetMappedColumn("first")
    AssertEqual "mOn mixed", 11, ImportModule.GetMappedColumn("mOn")
    CleanMockHeaderMap
End Sub

Public Sub Test_GetMappedColumn_AliasResolution()
    MockHeaderMap
    AssertEqual "Goes By -> 5", 5, ImportModule.GetMappedColumn("Goes By")
    AssertEqual "GoesBy -> 5", 5, ImportModule.GetMappedColumn("GoesBy")
    AssertEqual "Join Time -> 10", 10, ImportModule.GetMappedColumn(HDR_JOIN_TIME)
    AssertEqual "Thu -> 14", 14, ImportModule.GetMappedColumn("Thu")
    AssertEqual "Thurs -> 14", 14, ImportModule.GetMappedColumn("Thurs")
    AssertEqual "Pro Skill -> 16", 16, ImportModule.GetMappedColumn("Pro Skill")
    AssertEqual "ProSkill -> 16", 16, ImportModule.GetMappedColumn("ProSkill")
    AssertEqual "MC Project -> 21", 21, ImportModule.GetMappedColumn("MC Project")
    AssertEqual "MCP -> 21", 21, ImportModule.GetMappedColumn("MCP")
    CleanMockHeaderMap
End Sub

Public Sub Test_GetMappedColumn_MissingColumnReturnsZero()
    MockHeaderMap
    AssertEqual "Missing header = 0", 0, ImportModule.GetMappedColumn("NoSuchColumn")
    AssertEqual "Empty string = 0", 0, ImportModule.GetMappedColumn("")
    CleanMockHeaderMap
End Sub

Public Sub Test_GetMappedColumn_EmptySheet()
    CleanMockHeaderMap
    Dim ws As Worksheet
    Set ws = MockParticipantSheet()
    ' ws is completely blank -- no headers
    AssertEqual "Empty sheet returns 0", 0, ImportModule.GetMappedColumn("First")
    CleanMockParticipantSheet
End Sub

Public Sub Test_GetMappedColumn_DuplicateHeaderUsesFirst()
    Dim p As Worksheet
    Set p = ThisWorkbook.Sheets(PARAM_SHEET)
    p.Range(p.Cells(200, 1), p.Cells(260, 2)).ClearContents
    p.Cells(200, 1).Value = "ColMapKey"
    p.Cells(200, 2).Value = "ColIndex"
    p.Cells(201, 1).Value = "First": p.Cells(201, 2).Value = 3
    p.Cells(202, 1).Value = "First": p.Cells(202, 2).Value = 99   ' duplicate

    AssertEqual "Duplicate uses first occurrence", 3, ImportModule.GetMappedColumn("First")
    CleanMockHeaderMap
End Sub

' ============================================================
' Tests: SortCollection
' ============================================================
Public Sub Test_SortCollection_BasicOrder()
    Dim col As New Collection
    col.Add "Zebra", "Zebra"
    col.Add "Apple", "Apple"
    col.Add "Mango", "Mango"
    Dim sorted As Collection
    Set sorted = SortCollection(col)
    AssertEqual "Sort(1)=Apple", "Apple", sorted(1)
    AssertEqual "Sort(2)=Mango", "Mango", sorted(2)
    AssertEqual "Sort(3)=Zebra", "Zebra", sorted(3)
End Sub

Public Sub Test_SortCollection_SingleItem()
    Dim col As New Collection
    col.Add "OnlyItem", "OnlyItem"
    Dim sorted As Collection
    Set sorted = SortCollection(col)
    AssertEqual "Single item value", "OnlyItem", sorted(1)
    AssertEqual "Single item count", 1, sorted.Count
End Sub

Public Sub Test_SortCollection_EmptyCollection()
    Dim col As New Collection
    Dim sorted As Collection
    Set sorted = SortCollection(col)
    AssertEqual "Empty sort count=0", 0, sorted.Count
End Sub

' ============================================================
' Tests: CreateUniqueJobNumberList
' ============================================================
Public Sub Test_CreateUniqueJobNumberList_DeduplicatesAcrossDays()
    MockHeaderMap
    Dim ws As Worksheet
    Set ws = MockParticipantSheet()

    ' Row 3 = header row (matches FwParticipants); data from row 4 (JobNumbersModule).
    ws.Cells(3, 1).Value = "Minor or Adult"
    ws.Cells(3, 2).Value = "Registration OrganizationId"
    ws.Cells(3, 3).Value = "First"
    ws.Cells(3, 4).Value = "Last"
    ws.Cells(3, 5).Value = "Goes By"
    ws.Cells(3, 6).Value = "Age"
    ws.Cells(3, 7).Value = "CellPhone"
    ws.Cells(3, 8).Value = "Email"
    ws.Cells(3, 9).Value = "Join Date"
    ws.Cells(3, 10).Value = "Join Time"
    ws.Cells(3, 11).Value = "Mon"
    ws.Cells(3, 12).Value = "Tue"
    ws.Cells(3, 13).Value = "Wed"
    ws.Cells(3, 14).Value = "Thu"
    ws.Cells(3, 15).Value = "Fri"
    ws.Cells(3, 16).Value = "Pro Skill"
    ws.Cells(3, 17).Value = "Licensed"
    ws.Cells(3, 18).Value = "Int Skill"
    ws.Cells(3, 19).Value = "Nov Skill"
    ws.Cells(3, 20).Value = "MC"
    ws.Cells(3, 21).Value = "MC Project"
    ws.Cells(3, 22).Value = "Request"
    ws.Cells(3, 23).Value = "Job-Mon"
    ws.Cells(3, 24).Value = "Job-Tue"
    ws.Cells(3, 25).Value = "Job-Wed"
    ws.Cells(3, 26).Value = "Job-Thu"
    ws.Cells(3, 27).Value = "Job-Fri"

    ' Row 4: Job-Mon=J-01, Job-Fri=J-02
    ws.Cells(4, 1).Value = "Adult"
    ws.Cells(4, 3).Value = "Alice"
    ws.Cells(4, 4).Value = "Smith"
    ws.Cells(4, 23).Value = "J-01"
    ws.Cells(4, 27).Value = "J-02"

    ' Row 5: Job-Mon=J-01 (duplicate), Job-Tue=J-03
    ws.Cells(5, 1).Value = "Adult"
    ws.Cells(5, 3).Value = "Bob"
    ws.Cells(5, 4).Value = "Jones"
    ws.Cells(5, 23).Value = "J-01"
    ws.Cells(5, 24).Value = "J-03"

    Dim result As Collection
    Set result = CreateUniqueJobNumberList()
    AssertEqual "Job list count=3", 3, result.Count
    AssertEqual "Job list(1)=J-01", "J-01", result(1)
    AssertEqual "Job list(2)=J-02", "J-02", result(2)
    AssertEqual "Job list(3)=J-03", "J-03", result(3)

    CleanMockParticipantSheet
    CleanMockHeaderMap
End Sub

Public Sub Test_CreateUniqueJobNumberList_EmptySheet()
    MockHeaderMap
    Dim ws As Worksheet
    Set ws = MockParticipantSheet()
    ' ws is blank -- no data rows
    Dim result As Collection
    Set result = CreateUniqueJobNumberList()
    AssertEqual "Empty sheet job count=0", 0, result.Count
    CleanMockParticipantSheet
    CleanMockHeaderMap
End Sub
