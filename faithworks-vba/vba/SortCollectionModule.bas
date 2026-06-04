Option Explicit

'===============================================================================
' SortCollectionModule.bas
' Author: Steve Lashinski, 2026
' Sorts a Collection of strings alphabetically ascending.
' Uses bubble sort â€” adequate for typical volunteer counts (~200 items).
'
' Fix from original: counters changed from Integer to Long (Integer overflows
' at 32,767 items and would crash on large exports).
'===============================================================================

Public Function SortCollection(ByVal colInput As Collection) As Collection

    If colInput Is Nothing Then
        Set SortCollection = New Collection
        Exit Function
    End If

    If colInput.Count <= 1 Then
        Set SortCollection = colInput
        Exit Function
    End If

    Dim i    As Long
    Dim j    As Long
    Dim temp As Variant

    For i = 1 To colInput.Count - 1
        For j = i + 1 To colInput.Count
            If colInput(i) > colInput(j) Then
                temp = colInput(j)
                colInput.Remove j
                colInput.Add Item:=temp, key:=CStr(temp), Before:=i
            End If
        Next j
    Next i

    Set SortCollection = colInput

End Function
