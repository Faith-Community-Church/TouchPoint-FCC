Option Explicit

Private Sub DayOfWkLbl_Click()

End Sub

Sub DaysOfWeekCmbo_Change()

    Application.ScreenUpdating = False
    
    JobListBox.Hide
    DaysOfWeekCmbo.Visible = False
    
    Call PrintParticipantsJobDayModule.PrintParticipantsJobDay(DaysOfWeekCmbo.Value)
    
    Unload Me
    
    Application.ScreenUpdating = True
    
End Sub

Private Sub JobDayJobNumLbl_Click()

End Sub

Private Sub JobNumberCmbo_Change()
    
    Application.ScreenUpdating = False
    
    JobListBox.Hide
    JobNumberCmbo.Visible = False
    
    Call PrintJobModule.PrintJob(JobNumberCmbo.Value)
    
    Unload Me
    
    Application.ScreenUpdating = True
End Sub

Private Sub JobDayJobNumberCmbo_Change()
    
    Application.ScreenUpdating = False
    
    JobListBox.Hide
    JobDayJobNumberCmbo.Visible = False
    
    Call PrintJobDayModule.PrintJobDay(JobDayJobNumberCmbo.Value)
    
    Unload Me
    
    Application.ScreenUpdating = True
End Sub

Private Sub JobNumLbl_Click()

End Sub

Private Sub PrintCardsButton_Click()
    
    Application.ScreenUpdating = False
    
    JobListBox.Hide
    JobDayJobNumberCmbo.Visible = False
    
    Call MailMergePrintModule.RunMerge
    
    Unload Me
    
    Application.ScreenUpdating = True
    
End Sub

Private Sub UserForm_Initialize()

    Dim ws        As Worksheet
    Dim cJobNumbers As Collection
    Dim jobNumber As Variant
    Dim workdays(4) As String

    Set ws = SharedPrintHelpers.GetParticipantSheet()
    Set cJobNumbers = CreateUniqueJobNumberList

    workdays(0) = "Mon"
    workdays(1) = "Tue"
    workdays(2) = "Wed"
    workdays(3) = "Thu"
    workdays(4) = "Fri"

    Me.DaysOfWeekCmbo.Clear
    Me.JobDayJobNumberCmbo.Clear
    Me.JobNumberCmbo.Clear

    For Each jobNumber In cJobNumbers
        Me.JobNumberCmbo.AddItem jobNumber
    Next jobNumber

    Me.DaysOfWeekCmbo.List = workdays
    Me.JobDayJobNumberCmbo.List = workdays

End Sub
