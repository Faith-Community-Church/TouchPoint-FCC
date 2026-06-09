-- faithworks_volunteer_daily_totals.sql
-- Purpose: Daily headcount summary for FaithWorks adult (1865) and minor (1878) volunteer
--          registrations — total unique people per weekday (Mon–Fri), any time slot.
-- Author: (your church IT)
-- Date: 2026-06-09
--
-- Based on faithworks_volunteer_registration_responses.sql registration logic.
-- Day subgroups: Mon/Tue/Wed/Thu/Fri tags (00=AM, 01=PM, 02=EVE, 03=Family Day, NA=Not Available).
-- NA tags are excluded — only actual availability selections count.
-- A person with multiple time slots on the same day counts once for that day.

DECLARE @OrganizationIdAdult INT = 1865;  -- FaithWorks Adult Volunteer Registration
DECLARE @OrganizationIdMinor INT = 1878; -- FaithWorks Minor Volunteer Registration
DECLARE @AsOfDate DATETIME = GETDATE();

WITH CompletedRegistrations AS (
    SELECT DISTINCT
        r.RegistrationId,
        r.OrganizationId,
        r.CreatedDate,
        r.PeopleId AS RegistrantPeopleId
    FROM dbo.Registration r
    W.OrganizationId IN (@OrganizationIdAdult, @OrganizationIdMinor)
        AND r.CreatedDate <= @AsOfDate
),
RegisteredPeople AS (
    SELECT
        rp.RegPeopleId,
        rp.RegistrationId,
        rp.PeopleId,
        rp.CompletedDate,
        cr.OrganizationId
    FROM dbo.RegPeople rp
    INNER JOIN CompletedRegistrations cr ON cr.RegistrationId = rp.RegistrationId
    WHERE rp.CompletedDate IS NOT NULL
        AND rp.CompletedDate <= @AsOfDate
        AND rp.PeopleId IS NOT NULL
),
RankedRegs AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY PeopleId ORDER BY CompletedDate DESC) AS rn
    FROM RegisteredPeople
),
RegisteredVolunteers AS (
    SELECT
        rr.PeopleId,
        rr.OrganizationId
    FROM RankedRegs rr
    WHERE rr.rn = 1
),
VolunteerDays AS (
    SELECT DISTINCT
        rv.PeopleId,
        CASE
            WHEN mt.Name LIKE N'Mon%' THEN N'Monday'
            WHEN mt.Name LIKE N'Tue%' THEN N'Tuesday'
            WHEN mt.Name LIKE N'Wed%' THEN N'Wednesday'
            WHEN mt.Name LIKE N'Thu%' THEN N'Thursday'
            WHEN mt.Name LIKE N'Fri%' THEN N'Friday'
        END AS [Day]
    FROM RegisteredVolunteers rv
    INNER JOIN dbo.OrgMemMemTags omm
        ON omm.OrgId = rv.OrganizationId
        AND omm.PeopleId = rv.PeopleId
    INNER JOIN dbo.MemberTags mt
        ON mt.Id = omm.MemberTagId
        AND mt.OrgId = omm.OrgId
    WHERE (
            mt.Name LIKE N'Mon%'
            OR mt.Name LIKE N'Tue%'
            OR mt.Name LIKE N'Wed%'
            OR mt.Name LIKE N'Thu%'
            OR mt.Name LIKE N'Fri%'
        )
        AND RIGHT(mt.Name, 2) IN (N'00', N'01', N'02', N'03')  -- exclude NA (not available)
)
SELECT
    (SELECT COUNT(DISTINCT PeopleId) FROM VolunteerDays WHERE [Day] = N'Monday') AS [Monday],
    (SELECT COUNT(DISTINCT PeopleId) FROM VolunteerDays WHERE [Day] = N'Tuesday') AS [Tuesday],
    (SELECT COUNT(DISTINCT PeopleId) FROM VolunteerDays WHERE [Day] = N'Wednesday') AS [Wednesday],
    (SELECT COUNT(DISTINCT PeopleId) FROM VolunteerDays WHERE [Day] = N'Thursday') AS [Thursday],
    (SELECT COUNT(DISTINCT PeopleId) FROM VolunteerDays WHERE [Day] = N'Friday') AS [Friday];

