Option Explicit

'===============================================================================
' CollectUniqueValues.bas
' Returns a Collection containing one entry per unique non-empty string value
' found in the supplied range.  Uses a Variant array for speed â€” only one
' worksheet read regardless of range size.
'===============================================================================

Public Function CollectUniques(rng As Range) As Collection

    Dim varArray As Variant
    Dim var      As Variant
    Dim col      As Collection

    ' Guard: nothing passed or range is empty
    If rng Is Nothing Or WorksheetFunction.CountA(rng) = 0 Then
        Set CollectUniques = col   ' returns Nothing â€” callers must check
        Exit Function
    End If

    If rng.Count = 1 Then
        ' Single-cell range â€” no need for array conversion
        Set col = New Collection
        col.Add Item:=CStr(rng.Value), key:=CStr(rng.Value)
    Else
        varArray = rng.Value
        Set col = New Collection

        ' On Error Resume Next suppresses the error Excel raises when you try to
        ' add a duplicate key to a Collection â€” that is the intended behaviour here.
        On Error Resume Next
            For Each var In varArray
                If CStr(var) <> vbNullString Then
                    col.Add Item:=CStr(var), key:=CStr(var)
                End If
            Next var
        On Error GoTo 0
    End If

    Set CollectUniques = col

End Function
