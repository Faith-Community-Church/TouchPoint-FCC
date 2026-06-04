Option Explicit

'===============================================================================
' PrintButtonModule.bas
' Author: Steve Lashinski, 2026
' Adds a Print button to the FwParticipants sheet header row and handles
' the click event that opens the JobListBox print-options form.
'===============================================================================

'===============================================================================
' PrintButton
' Called by ImportModule after a successful import to place the Print button.
' currentSheet â€” the FwParticipants worksheet to add the button to.
'===============================================================================
Public Sub PrintButton(currentSheet As Worksheet)

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False

    ' Remove any existing Print button first
    currentSheet.Buttons.Delete

    ' Anchor the button at cell E1
    Dim anchorCell As Range
    Set anchorCell = currentSheet.Range("E1")

    Dim btn As Button
    Set btn = currentSheet.Buttons.Add( _
        anchorCell.Left + (anchorCell.Width / 6), _
        anchorCell.Top + (anchorCell.Height / 6), _
        10, anchorCell.Height)

    With btn
        .Height = 30
        .Width = 100
        .OnAction = "PrintButton_Click"
        .Caption = "Print"
        .Name = "PrintBtn"
        .Font.Bold = True
        .Font.Size = 14
    End With

    Exit Sub

ErrHandler:
    MsgBox "Could not add Print button: " & Err.Description, _
           vbExclamation, "FaithWorks"

End Sub


'===============================================================================
' PrintButton_Click
' Fires when the user clicks the Print button on the participant sheet.
' Opens the JobListBox form with the day-of-week selector visible.
'===============================================================================
Public Sub PrintButton_Click()
    JobListBox.DaysOfWeekCmbo.Visible = True
    JobListBox.JobDayJobNumberCmbo.Visible = True
    JobListBox.JobNumberCmbo.Visible = True
    JobListBox.StartUpPosition = 2
    JobListBox.Show
End Sub
