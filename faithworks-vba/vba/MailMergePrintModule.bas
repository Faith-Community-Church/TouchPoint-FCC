Option Explicit

'===============================================================================
' MailMergePrintModule.bas
' Opens a Word mail merge template, connects it to the FwParticipants data,
' and runs the merge to produce volunteer cards.
'
' BUGS FIXED FROM ORIGINAL:
'   1. customerFilename was undeclared (implicit Variant) -- now Dim'd as String
'   2. participantRange was undeclared -- now Dim'd as Long
'   3. Connection string used the literal text "StrMMSrc" instead of the
'      variable value -- corrected to use & StrMMSrc &
'===============================================================================

Public Sub RunMerge()

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False

    ' -- 1. Identify participant sheet
    Dim participantsWs As Worksheet
    Set participantsWs = SharedPrintHelpers.GetParticipantSheet()
    If participantsWs Is Nothing Then GoTo Cleanup

    Dim participantRange As Long
    participantRange = participantsWs.Cells(participantsWs.Rows.Count, "A").End(xlUp).Row

    ' -- 2. Browse for the Word mail merge document
    Dim mailMergeDocPath As String
    mailMergeDocPath = Application.GetOpenFilename( _
        FileFilter:="Word Files (*.docx),*.docx", _
        Title:="Select the Volunteer Card Mail Merge Document")

    If mailMergeDocPath = "False" Or mailMergeDocPath = "" Then GoTo Cleanup

    ThisWorkbook.Sheets(PARAM_SHEET).Range(PARAM_MAIL_MERGE_DOC).Value = mailMergeDocPath

    If Dir(mailMergeDocPath) = "" Then
        MsgBox "Cannot find the selected file:" & vbCr & mailMergeDocPath, _
               vbExclamation, "FaithWorks Mail Merge"
        GoTo Cleanup
    End If

    ' -- 3. Build SQL covering all columns up to the last used header
    Dim lastCol As Long
    lastCol = participantsWs.Cells(3, participantsWs.Columns.Count).End(xlToLeft).Column
    Dim lastColLetter As String
    lastColLetter = Split(participantsWs.Cells(3, lastCol).Address(True, True), "$")(1)

    Dim participantsWsName As String
    participantsWsName = participantsWs.Name

    Dim StrMMSrc As String
    StrMMSrc = ThisWorkbook.FullName

    Dim sqlQuery As String
    sqlQuery = "SELECT * FROM [" & participantsWsName & "$A3:" & _
               lastColLetter & participantRange & "]"

    ' -- 4. Launch Word (or attach to running instance)
    Dim wdApp As Object
    Dim wdDoc As Object

    On Error Resume Next
    Set wdApp = GetObject(, "Word.Application")
    On Error GoTo ErrHandler

    If wdApp Is Nothing Then
        Set wdApp = CreateObject("Word.Application")
        If wdApp Is Nothing Then
            MsgBox "Could not launch Microsoft Word. Please ensure Word is installed.", _
                   vbExclamation, "FaithWorks Mail Merge"
            GoTo Cleanup
        End If
    End If

    ' -- 5. Open the merge document and run the merge
    With wdApp
        .Visible = True
        .WordBasic.DisableAutoMacros
        .DisplayAlerts = 0   ' wdAlertsNone

        Set wdDoc = .Documents.Open(mailMergeDocPath, ReadOnly:=False, AddToRecentFiles:=False)

        With wdDoc
            With .MailMerge
                .MainDocumentType = 0     ' wdFormLetters
                .Destination = 0          ' wdSendToNewDocument
                .SuppressBlankLines = True
                .OpenDataSource _
                    Name:=StrMMSrc, _
                    ReadOnly:=True, _
                    AddToRecentFiles:=False, _
                    LinkToSource:=False, _
                    Connection:="Provider=Microsoft.ACE.OLEDB.12.0;" & _
                                "User ID=Admin;" & _
                                "Data Source=" & StrMMSrc & ";" & _
                                "Mode=Read;" & _
                                "Extended Properties=""HDR=YES;IMEX=1;""", _
                    SQLStatement:=sqlQuery, _
                    SubType:=1   ' wdMergeSubTypeAccess

                With .DataSource
                    .FirstRecord = -1   ' wdDefaultFirstRecord
                    .LastRecord = -16   ' wdDefaultLastRecord
                End With

                .Execute Pause:=False
            End With
            .Close SaveChanges:=False
        End With
    End With

    GoTo Cleanup

ErrHandler:
    MsgBox "Mail merge error " & Err.Number & ": " & Err.Description & vbCr & vbCr & _
           "If Word opened but the merge did not complete, close Word and try again.", _
           vbExclamation, "FaithWorks Mail Merge"

Cleanup:
    On Error Resume Next
    Set wdDoc = Nothing
    Set wdApp = Nothing
    Application.ScreenUpdating = True

End Sub
