# OnEnroll Script: Add Spouse to Organization
# This script automatically adds the spouse of the enrolling person to the same organization

people_id = Data.PeopleId
org_id = int(Data.OrganizationId)

# Get spouse person object (could be None)
spouse = model.GetSpouse(people_id)

# Only proceed if spouse exists
if spouse is not None:
    spouse_id = spouse.PeopleId

    # Check if spouse is already in the org
    if not model.InOrg(spouse_id, org_id):
        model.AddMemberToOrg(spouse_id, org_id)
