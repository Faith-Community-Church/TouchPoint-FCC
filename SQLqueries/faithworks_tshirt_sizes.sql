-- faithworks_tshirt_sizes.sql
-- Purpose: First name, last name, and t-shirt size for active FaithWorks volunteer registrations.
-- Author: (your church IT)
-- Date: 2026-06-04
--
-- Involvements:
--   1865 = FaithWorks Adult Volunteer Registration
--   1878 = FaithWorks Minor Volunteer Registration
--
-- T-shirt size subgroups (MemberTags.Name on the member's involvement):
--   Youth:  Y-SM, Y-M, Y-L, Y-XL
--   Adult:  A-SM, A-M, A-L, A-XL, A-2XL
--   Other:  NoShirt

DECLARE @OrganizationIdAdult INT = 1865;
DECLARE @OrganizationIdMinor INT = 1878;
DECLARE @AsOfDate DATETIME = GETDATE();

WITH ActiveMembers AS (
    SELECT
        om.PeopleId,
        om.OrganizationId
    FROM dbo.OrganizationMembers om
    WHERE om.OrganizationId IN (@OrganizationIdAdult, @OrganizationIdMinor)
        AND ISNULL(om.Pending, 0) = 0
        AND om.MemberTypeId NOT IN (230, 311)  -- InActive, Prospect
        AND om.EnrollmentDate <= @AsOfDate
)
SELECT
    p.FirstName AS [First],
    p.LastName AS [Last],
    shirt.ShirtSize AS [T-Shirt Size]
FROM ActiveMembers am
JOIN dbo.People p ON p.PeopleId = am.PeopleId
OUTER APPLY (
    SELECT TOP 1 mt.Name AS ShirtSize
    FROM dbo.OrgMemMemTags omm
    INNER JOIN dbo.MemberTags mt ON mt.Id = omm.MemberTagId AND mt.OrgId = omm.OrgId
    WHERE omm.OrgId = am.OrganizationId
        AND omm.PeopleId = am.PeopleId
        AND mt.Name IN (
            N'Y-SM', N'Y-M', N'Y-L', N'Y-XL',
            N'A-SM', N'A-M', N'A-L', N'A-XL', N'A-2XL',
            N'NoShirt'
        )
) shirt
ORDER BY p.LastName, p.FirstName;

