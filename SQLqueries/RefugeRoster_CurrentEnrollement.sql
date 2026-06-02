-- RefugeRoster_CurrentEnrollement.sql
-- Purpose: Combined member roster for involvements 83 and 84 with parent contact info. To be updated with new Inv #s when re-create using new Reg Form in Aug 2026.
-- Author: Jake Pierson / Cursor AI
-- Date: 2026-06-02
--
-- One row per person (deduplicated if enrolled in both involvements).
-- Sorted by: Grade, Gender and then Last Name. Includes current Attendance Percentage for the respective involvement.
-- Parent fields come from the family head of household and spouse.

DECLARE @OrganizationId1 INT = 83;
DECLARE @OrganizationId2 INT = 84;
DECLARE @AsOfDate DATETIME = GETDATE();

WITH ActiveMembers AS (
    SELECT
        om.PeopleId,
        om.OrganizationId,
        om.AttendPct,
        ROW_NUMBER() OVER (
            PARTITION BY om.PeopleId
            ORDER BY om.EnrollmentDate DESC, om.OrganizationId
        ) AS rn
    FROM dbo.OrganizationMembers om
    WHERE om.OrganizationId IN (@OrganizationId1, @OrganizationId2)
        AND ISNULL(om.Pending, 0) = 0
        AND om.MemberTypeId NOT IN (230, 311)  -- InActive, Prospect
        AND om.EnrollmentDate <= @AsOfDate
)
SELECT
    p.FirstName AS [First],
    p.LastName AS [Last],
    g.Code AS [Gender],
    gl.Description AS [Grade],
    p.Age AS [Age],
    am.AttendPct AS [Attend %],
    NULLIF(LTRIM(RTRIM(
        ISNULL(NULLIF(h.PreferredName, N''), h.FirstName) + N' ' + h.LastName
    )), N'') AS [Parent 1],
    NULLIF(LTRIM(RTRIM(
        ISNULL(NULLIF(s.PreferredName, N''), s.FirstName)
        + N' '
        + ISNULL(NULLIF(s.LastName, N''), h.LastName)
    )), N'') AS [Parent 2],
    CASE
        WHEN NULLIF(LTRIM(RTRIM(h.CellPhone)), N'') IS NOT NULL
            AND NULLIF(LTRIM(RTRIM(s.CellPhone)), N'') IS NOT NULL
            THEN dbo.FmtPhone(h.CellPhone) + N' / ' + dbo.FmtPhone(s.CellPhone)
        WHEN NULLIF(LTRIM(RTRIM(h.CellPhone)), N'') IS NOT NULL
            THEN dbo.FmtPhone(h.CellPhone)
        WHEN NULLIF(LTRIM(RTRIM(s.CellPhone)), N'') IS NOT NULL
            THEN dbo.FmtPhone(s.CellPhone)
        ELSE NULL
    END AS [Parent Cell Phone],
    CASE
        WHEN NULLIF(LTRIM(RTRIM(h.EmailAddress)), N'') IS NOT NULL
            AND NULLIF(LTRIM(RTRIM(s.EmailAddress)), N'') IS NOT NULL
            THEN h.EmailAddress + N' / ' + s.EmailAddress
        WHEN NULLIF(LTRIM(RTRIM(h.EmailAddress)), N'') IS NOT NULL
            THEN h.EmailAddress
        WHEN NULLIF(LTRIM(RTRIM(s.EmailAddress)), N'') IS NOT NULL
            THEN s.EmailAddress
        ELSE NULL
    END AS [Parent Email]
FROM ActiveMembers am
JOIN dbo.People p ON p.PeopleId = am.PeopleId
JOIN dbo.Families f ON f.FamilyId = p.FamilyId
LEFT JOIN dbo.People h ON h.PeopleId = f.HeadOfHouseholdId
LEFT JOIN dbo.People s ON s.PeopleId = f.HeadOfHouseholdSpouseId
LEFT JOIN lookup.GradeLevel gl ON gl.Id = p.GradeLevelId
LEFT JOIN lookup.Gender g ON g.Id = p.GenderId
WHERE am.rn = 1
ORDER BY ISNULL(gl.Id, 9999), ISNULL(g.Id, 99), p.LastName, p.FirstName;

