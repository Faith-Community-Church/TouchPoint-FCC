-- faithworks_people_attending.sql
-- Purpose: List FaithWorks adult (1865) and minor (1878) volunteers who answered
--          the Menu question "Number of people attending:" with a value greater than 0.
-- Author: (your church IT)
-- Date: 2026-06-09
--
-- Excel export format: "Number of people attending:: 3" (option text ends with ":")
-- Question prompt: "Please let us know how many people will be attending our
-- celebration dinner..."
--
-- Menu answers: RegAnswer JSON array (e.g. ["3"]) and/or OrgMemMemTags.Number on
-- the menu option tag "Number of people attending:"

DECLARE @OrganizationIdAdult INT = 1865;  -- FaithWorks Adult Volunteer Registration
DECLARE @OrganizationIdMinor INT = 1878; -- FaithWorks Minor Volunteer Registration
DECLARE @AsOfDate DATETIME = GETDATE();
DECLARE @MenuOptionTag NVARCHAR(200) = N'Number of people attending:';

WITH CompletedRegistrations AS (
    SELECT DISTINCT
        r.RegistrationId,
        r.OrganizationId,
        r.CreatedDate
    FROM dbo.Registration r
    WHERE r.OrganizationId IN (@OrganizationIdAdult, @OrganizationIdMinor)
        AND r.CreatedDate <= @AsOfDate
),
RegisteredPeople AS (
    SELECT
        rp.RegPeopleId,
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
        ROW_NUMBER() OVER (
            PARTITION BY PeopleId, OrganizationId
            ORDER BY CompletedDate DESC
        ) AS rn
    FROM RegisteredPeople
),
-- Match the celebration-dinner menu question by prompt or option text in Options JSON
AttendingQuestions AS (
    SELECT
        rq.RegQuestionId,
        rq.OrganizationId,
        rq.Label,
        rq.Options
    FROM dbo.RegQuestion rq
    WHERE rq.OrganizationId IN (@OrganizationIdAdult, @OrganizationIdMinor)
        AND rq.QuestionSubTypeId = 1  -- Menu
        AND (
            LOWER(rq.Label) LIKE N'%celebration dinner%'
            OR LOWER(rq.Label) LIKE N'%people attending%'
            OR LOWER(rq.Label) LIKE N'%attending our%'
            OR EXISTS (
                SELECT 1
                FROM OPENJSON(rq.Options) WITH (OptionText NVARCHAR(500) '$.text') opt
                WHERE LOWER(opt.OptionText) LIKE N'%people attending%'
            )
        )
),
MenuRegAnswers AS (
    SELECT
        rr.PeopleId,
        rr.OrganizationId,
        ra.AnswerValue
    FROM RankedRegs rr
    INNER JOIN dbo.RegAnswer ra ON ra.RegPeopleId = rr.RegPeopleId
    INNER JOIN AttendingQuestions aq ON aq.RegQuestionId = ra.RegQuestionId
    WHERE rr.rn = 1
        AND ra.AnswerValue IS NOT NULL
),
ParsedMenuJson AS (
    SELECT
        mra.PeopleId,
        mra.OrganizationId,
        -- Handle ["3"], ["0"], or double-encoded JSON strings
        CASE
            WHEN LEFT(LTRIM(mra.AnswerValue), 1) = '[' THEN mra.AnswerValue
            WHEN LEFT(LTRIM(mra.AnswerValue), 1) = '"'
                AND JSON_VALUE(mra.AnswerValue, '$') LIKE '[%'
                THEN JSON_VALUE(mra.AnswerValue, '$')
            ELSE CONCAT(N'["', REPLACE(REPLACE(mra.AnswerValue, '\', ''), '"', ''), N'"]')
        END AS JsonArray
    FROM MenuRegAnswers mra
),
RegAnswerCounts AS (
    SELECT
        pmj.PeopleId,
        pmj.OrganizationId,
        SUM(
            ISNULL(TRY_CAST(NULLIF(LTRIM(RTRIM(j.[value])), '') AS INT), 0)
        ) AS AttendingCount
    FROM ParsedMenuJson pmj
    CROSS APPLY OPENJSON(pmj.JsonArray) j
    GROUP BY pmj.PeopleId, pmj.OrganizationId
),
TagAnswerCounts AS (
    SELECT
        rr.PeopleId,
        rr.OrganizationId,
        SUM(omm.Number) AS AttendingCount
    FROM RankedRegs rr
    INNER JOIN dbo.OrgMemMemTags omm
        ON omm.OrgId = rr.OrganizationId
        AND omm.PeopleId = rr.PeopleId
    INNER JOIN dbo.MemberTags mt
        ON mt.Id = omm.MemberTagId
        AND mt.OrgId = omm.OrgId
    WHERE rr.rn = 1
        AND omm.Number > 0
        AND (
            mt.Name = @MenuOptionTag
            OR LOWER(mt.Name) LIKE N'%people attending%'
        )
    GROUP BY rr.PeopleId, rr.OrganizationId
),
AllCounts AS (
    SELECT PeopleId, OrganizationId, AttendingCount, 1 AS SourcePriority
    FROM RegAnswerCounts
    WHERE AttendingCount > 0

    UNION ALL

    SELECT PeopleId, OrganizationId, AttendingCount, 2 AS SourcePriority
    FROM TagAnswerCounts
    WHERE AttendingCount > 0
),
BestAnswerPerPerson AS (
    SELECT
        ac.PeopleId,
        ac.OrganizationId,
        ac.AttendingCount,
        ROW_NUMBER() OVER (
            PARTITION BY ac.PeopleId, ac.OrganizationId
            ORDER BY ac.SourcePriority, ac.AttendingCount DESC
        ) AS rn
    FROM AllCounts ac
),
Attendees AS (
    SELECT
        CASE bap.OrganizationId
            WHEN @OrganizationIdAdult THEN N'Adult'
            WHEN @OrganizationIdMinor THEN N'Minor'
            ELSE N'Unknown'
        END AS [Minor or Adult],
        p.FirstName AS [First],
        p.LastName AS [Last],
        ISNULL(p.PreferredName, p.NickName) AS [Goes By],
        p.CellPhone,
        p.EmailAddress AS [Email],
        bap.AttendingCount AS [Number of People Attending]
    FROM BestAnswerPerPerson bap
    JOIN dbo.People p ON p.PeopleId = bap.PeopleId
    WHERE bap.rn = 1
)
SELECT
    [Minor or Adult],
    [First],
    [Last],
    [Goes By],
    [CellPhone],
    [Email],
    [Number of People Attending]
FROM (
    SELECT
        0 AS SortOrder,
        NULL AS [Minor or Adult],
        N'GRAND TOTAL' AS [First],
        NULL AS [Last],
        NULL AS [Goes By],
        NULL AS [CellPhone],
        NULL AS [Email],
        ISNULL(SUM([Number of People Attending]), 0) AS [Number of People Attending]
    FROM Attendees

    UNION ALL

    SELECT
        1 AS SortOrder,
        [Minor or Adult],
        [First],
        [Last],
        [Goes By],
        [CellPhone],
        [Email],
        [Number of People Attending]
    FROM Attendees
) report
ORDER BY SortOrder, [Last], [First];


-- ==========================================
-- DISCOVERY: Uncomment if the report is empty
-- ==========================================
/*
-- Find the menu question and sample answers
SELECT
    rq.OrganizationId,
    rq.RegQuestionId,
    rq.Label,
    rq.QuestionSubTypeId,
    rq.Options
FROM dbo.RegQuestion rq
WHERE rq.OrganizationId IN (1865, 1878)
ORDER BY rq.OrganizationId, rq.[Order];

SELECT TOP 50
    r.OrganizationId,
    rq.Label,
    ra.AnswerValue,
    p.FirstName,
    p.LastName
FROM dbo.RegAnswer ra
INNER JOIN dbo.RegPeople rp ON rp.RegPeopleId = ra.RegPeopleId
INNER JOIN dbo.Registration r ON r.RegistrationId = rp.RegistrationId
LEFT JOIN dbo.RegQuestion rq ON rq.RegQuestionId = ra.RegQuestionId
INNER JOIN dbo.People p ON p.PeopleId = rp.PeopleId
WHERE r.OrganizationId IN (1865, 1878)
    AND rq.QuestionSubTypeId = 1
ORDER BY rp.CompletedDate DESC;

SELECT
    omm.OrgId,
    mt.Name AS TagName,
    omm.Number,
    p.FirstName,
    p.LastName
FROM dbo.OrgMemMemTags omm
INNER JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
INNER JOIN dbo.People p ON p.PeopleId = omm.PeopleId
WHERE omm.OrgId IN (1865, 1878)
    AND LOWER(mt.Name) LIKE '%attending%'
ORDER BY omm.OrgId, p.LastName, p.FirstName;
*/

