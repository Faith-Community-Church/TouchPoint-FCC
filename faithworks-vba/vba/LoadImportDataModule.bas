Option Explicit

'===============================================================================
' LoadImportDataModule.bas
' Author: Steve Lashinski, 2026
' Backward-compatibility stub only.
' The original LoadWorksheet() called the old Power Query / OLEDB logic.
' It now simply delegates to ImportModule.FaithWorksImport.
' Do not add new logic here.
'===============================================================================

Public Sub LoadWorksheet(query As Object, currentSheet As Worksheet)
    Call ImportModule.FaithWorksImport
End Sub
