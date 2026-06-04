'===============================================================================
' UserForm:  ImportButton
' Author: Steve Lashinski, 2026
' Purpose:   Launched by the Import Volunteer Data shape button on
'            FwParticipants. Calls FaithWorksImport then closes itself.
' Trigger:   ButtonActions.ShowImportForm  (OnAction of btn_ImportVolunteerData)
'===============================================================================

Private Sub cmdImport_Click()
    ImportModule.FaithWorksImport
    Unload Me
End Sub
