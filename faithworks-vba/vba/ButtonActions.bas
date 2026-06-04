'===============================================================================
' ButtonActions.bas
' Author: Steve Lashinski, 2026
' Purpose:   Public OnAction entry points for all shape buttons on
'            FwParticipants. Must be Public Subs in a standard module —
'            sheet modules and ThisWorkbook are not valid OnAction targets.
' Buttons:   btn_ImportVolunteerData  -> ShowImportForm
'            btn_PrintRoster          -> PrintButton_Click (PrintButtonModule)
'===============================================================================
Option Explicit

Public Sub ShowImportForm()
    ' Opens the ImportButton UserForm
    ImportModule.FaithWorksImport
End Sub

Public Sub ShowPrintRosterForm()
    ' Delegates directly to the existing print click handler
    ' which opens the JobListBox form
    PrintButtonModule.PrintButton_Click
End Sub
