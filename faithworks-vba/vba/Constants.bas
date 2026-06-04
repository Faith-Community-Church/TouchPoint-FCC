Option Explicit

'===============================================================================
' Constants.bas
' Author: Steve Lashinski, 2026
' Central home for all header names, named range keys, layout sizes, and
' colour values. If TouchPoint renames a column, update it here only.
' Non-developer note: a Const is like a named cell -- it gives a readable
' name to a value you would otherwise have to hunt through many places.
'===============================================================================

' -- TouchPoint export header names (exact spelling from SELECT aliases) -------
Public Const HDR_MINOR_ADULT  As String = "Minor or Adult"
Public Const HDR_REG_ORG_ID   As String = "Registration OrganizationId"
Public Const HDR_FIRST        As String = "First"
Public Const HDR_LAST         As String = "Last"
Public Const HDR_GOES_BY      As String = "GoesBy"       ' alias for "Goes By"
Public Const HDR_AGE          As String = "Age"
Public Const HDR_PHONE        As String = "Phone"        ' alias for "CellPhone"
Public Const HDR_EMAIL        As String = "Email"
Public Const HDR_JOIN_DATE    As String = "Join Date"    ' involvement enroll / reg complete
Public Const HDR_JOIN_TIME    As String = "Join Time"
Public Const HDR_MON          As String = "Mon"
Public Const HDR_TUE          As String = "Tue"
Public Const HDR_WED          As String = "Wed"
Public Const HDR_THU          As String = "Thurs"        ' alias for "Thu"
Public Const HDR_FRI          As String = "Fri"
Public Const HDR_PRO_SKILL    As String = "ProSkill"     ' alias for "Pro Skill"
Public Const HDR_LICENSED     As String = "Licensed"
Public Const HDR_INT_SKILL    As String = "IntSkill"     ' alias for "Int Skill"
Public Const HDR_NOV_SKILL    As String = "NovSkill"     ' alias for "Nov Skill"
Public Const HDR_MC           As String = "MC"
Public Const HDR_MCP          As String = "MCP"          ' alias for "MC Project"

' -- Job assignment columns (appended after col S on import) -------------------
Public Const HDR_REQUEST      As String = "Request"
Public Const HDR_JOB_MON      As String = "Job-Mon"
Public Const HDR_JOB_TUE      As String = "Job-Tue"
Public Const HDR_JOB_WED      As String = "Job-Wed"
Public Const HDR_JOB_THU      As String = "Job-Thu"
Public Const HDR_JOB_FRI      As String = "Job-Fri"

' -- Parameters sheet named range keys ----------------------------------------
Public Const PARAM_SHEET          As String = "Parameters"
Public Const PARAM_PARTICIPANT_WS As String = "ParticipantSheetName"
Public Const PARAM_TEMP_SHEET     As String = "TempSheetName"
Public Const PARAM_MAIL_MERGE_DOC As String = "MailMergeDoc"
Public Const PARAM_HEADER_MAP_ROW As Long = 200

' -- Table / font formatting (must match workbook) -----------------------------
Public Const FW_TABLE_STYLE   As String = "FW Table Style"
Public Const FW_FONT_NAME     As String = "Times New Roman"
Public Const FW_FONT_SIZE_HDR As Integer = 13

' -- Colour indices for double-click day-highlight feature ---------------------
' (Excel legacy ColorIndex palette values)
Public Const COLOR_MON      As Integer = 26   ' purple
Public Const COLOR_TUE      As Integer = 49   ' dark teal
Public Const COLOR_WED      As Integer = 46   ' orange
Public Const COLOR_THU      As Integer = 27   ' yellow
Public Const COLOR_FRI      As Integer = 4    ' green
Public Const COLOR_TEXT_ON  As Integer = 2    ' white text when highlighted
Public Const COLOR_TEXT_OFF As Integer = 1    ' black text when cleared

' -- Print layout sizes --------------------------------------------------------
Public Const PRINT_FONT_HEADER  As Integer = 60
Public Const PRINT_FONT_BODY    As Integer = 18
Public Const PRINT_FONT_JOB_HDR As Integer = 24
Public Const COL_WIDTH_LAST     As Double = 22
Public Const COL_WIDTH_FIRST    As Double = 22
Public Const COL_WIDTH_JOB      As Double = 10

' -- Workday display names (used by JobListBox and JobDayClass) ----------------
Public Const WORKDAY_MON As String = "Mon"
Public Const WORKDAY_TUE As String = "Tue"
Public Const WORKDAY_WED As String = "Wed"
Public Const WORKDAY_THU As String = "Thu"
Public Const WORKDAY_FRI As String = "Fri"
