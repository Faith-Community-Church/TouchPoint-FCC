-- (saved in repo as FaithWorksMagicToolSQL.sql)
-- Purpose: Registration form responses for FaithWorks adult (1865) and minor (1878) volunteer
--          registrations; one row per person. [Minor or Adult] / subgroups / MC project reflect
--          the single kept registration: most recent CompletedDate across both orgs (ties arbitrary).
-- Uses new Registration Form architecture with subgroups for day/time and skill levels.
-- Prep data for mail merge of volunteers who completed registration.
-- Author: FCC IT
-- Date: 2026-04-23
--
-- Subgroup Legend:
--   Day/Time Subgroups: Mon00/01/02, Tue00/01/02, etc. (00=AM, 01=PM, 02=EVE)
--      00 = AM
--      01 = PM
--      02 = EVE
--      03 = Monday Only, Family Day (displayed as Family Day in output)
--   Skill prefixes: PRO_, LC_, INT_, NOV_, MC_ (displays value after underscore)
--      PRO_ = Pro Skill
--      LC_ = Licensed
--      INT_ = Int Skill
--      NOV_ = Nov Skill
--   MC_ = Missional Community
--   MC Project: Text question "Please tell us which MC project you're volunteering for"

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
    WHERE r.OrganizationId IN (@OrganizationIdAdult, @OrganizationIdMinor)
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
-- One row per person: latest completed RegPeople across adult+minor; rn>1 drops older same-person rows
RankedRegs AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY PeopleId ORDER BY CompletedDate DESC) AS rn
    FROM RegisteredPeople
)
SELECT
    -- Filter column: which involvement this row belongs to
    CASE rr.OrganizationId
        WHEN @OrganizationIdAdult THEN N'Adult'
        WHEN @OrganizationIdMinor THEN N'Minor'
        ELSE N'Unknown'
    END AS [Minor or Adult],
    rr.OrganizationId AS [Registration OrganizationId],

    -- General Info
    p.FirstName AS [First],
    p.LastName AS [Last],
    ISNULL(p.PreferredName, p.NickName) AS [Goes By],
    p.Age,
    p.CellPhone,
    p.EmailAddress AS [Email],

    -- Day/Time Subgroups: Mon, Tue, Wed, Thu, Fri
    -- Format: AM | PM | EVE | Family Day (00=AM, 01=PM, 02=EVE, 03=Monday-only Family Day per subgroup legend)
    STUFF((
        SELECT N' | ' + CASE RIGHT(mt.Name, 2)
            WHEN N'00' THEN N'AM'
            WHEN N'01' THEN N'PM'
            WHEN N'02' THEN N'EVE'
            WHEN N'03' THEN N'Family Day'
            ELSE RIGHT(mt.Name, 2)
        END
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'Mon%'
        ORDER BY RIGHT(mt.Name, 2)
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Mon],

    STUFF((
        SELECT N' | ' + CASE RIGHT(mt.Name, 2)
            WHEN N'00' THEN N'AM'
            WHEN N'01' THEN N'PM'
            WHEN N'02' THEN N'EVE'
            WHEN N'03' THEN N'Family Day'
            ELSE RIGHT(mt.Name, 2)
        END
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'Tue%'
        ORDER BY RIGHT(mt.Name, 2)
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Tue],

    STUFF((
        SELECT N' | ' + CASE RIGHT(mt.Name, 2)
            WHEN N'00' THEN N'AM'
            WHEN N'01' THEN N'PM'
            WHEN N'02' THEN N'EVE'
            WHEN N'03' THEN N'Family Day'
            ELSE RIGHT(mt.Name, 2)
        END
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'Wed%'
        ORDER BY RIGHT(mt.Name, 2)
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Wed],

    STUFF((
        SELECT N' | ' + CASE RIGHT(mt.Name, 2)
            WHEN N'00' THEN N'AM'
            WHEN N'01' THEN N'PM'
            WHEN N'02' THEN N'EVE'
            WHEN N'03' THEN N'Family Day'
            ELSE RIGHT(mt.Name, 2)
        END
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'Thu%'
        ORDER BY RIGHT(mt.Name, 2)
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Thu],

    STUFF((
        SELECT N' | ' + CASE RIGHT(mt.Name, 2)
            WHEN N'00' THEN N'AM'
            WHEN N'01' THEN N'PM'
            WHEN N'02' THEN N'EVE'
            WHEN N'03' THEN N'Family Day'
            ELSE RIGHT(mt.Name, 2)
        END
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'Fri%'
        ORDER BY RIGHT(mt.Name, 2)
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Fri],

    -- Skill Level Subgroups: PRO_, LC_, INT_, NOV_, MC_
    -- Value = everything after the prefix, | separator for multiple
    STUFF((
        SELECT N' | ' + SUBSTRING(mt.Name, 5, 200)
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'PRO_%'
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Pro Skill],

    STUFF((
        SELECT N' | ' + SUBSTRING(mt.Name, 4, 200)
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'LC_%'
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Licensed],

    STUFF((
        SELECT N' | ' + SUBSTRING(mt.Name, 5, 200)
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'INT_%'
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Int Skill],

    STUFF((
        SELECT N' | ' + SUBSTRING(mt.Name, 5, 200)
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'NOV_%'
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [Nov Skill],

    STUFF((
        SELECT N' | ' + SUBSTRING(mt.Name, 4, 200)
        FROM dbo.OrgMemMemTags omm
        JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
        WHERE omm.OrgId = rr.OrganizationId AND omm.PeopleId = p.PeopleId
            AND mt.Name LIKE N'MC_%'
        FOR XML PATH(N''), TYPE
    ).value(N'.', N'nvarchar(max)'), 1, 3, N'') AS [MC],

    -- MC Project: Text question from registration form (scoped to this row’s org)
    (SELECT TOP 1 ra.AnswerValue
     FROM dbo.RegAnswer ra
     INNER JOIN dbo.RegQuestion rq ON rq.RegQuestionId = ra.RegQuestionId
     WHERE ra.RegPeopleId = rr.RegPeopleId
         AND rq.OrganizationId = rr.OrganizationId
         AND rq.Label LIKE N'%MC project%') AS [MC Project]

FROM RankedRegs rr
JOIN dbo.People p ON p.PeopleId = rr.PeopleId
WHERE rr.rn = 1

ORDER BY [Minor or Adult], p.LastName, p.FirstName;


-- ==========================================
-- DIAGNOSTIC: Registration questions by org (IDs match DECLARE block above)
-- ==========================================
/*
SELECT
    rq.OrganizationId,
    rq.RegQuestionId,
    rq.Label AS Question,
    rq.QuestionTypeId
FROM dbo.RegQuestion rq
WHERE rq.OrganizationId IN (1865, 1878)
ORDER BY rq.OrganizationId, rq.[Order]
*/


-- ==========================================
-- DIAGNOSTIC: Subgroups (MemberTags) per org (IDs match DECLARE block above)
-- ==========================================
/*
SELECT
    mt.OrgId,
    mt.Id,
    mt.Name
FROM dbo.MemberTags mt
WHERE mt.OrgId IN (1865, 1878)
ORDER BY mt.OrgId, mt.Name
*/
