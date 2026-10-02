#Roles=Admin
# Script: RejoinPastMembers.py
# Purpose: Preview people who were enrolled in one involvement during a date
#   range (including those who dropped during the range) and re-join the ones
#   you select. Restores the member type, subgroups, and member extra values
#   from that drop, and puts the original enrollment date back on the new
#   membership.
# Author: Jake Pierson
# Date: 2026-10-02
#
# Install: Special Content -> Python Scripts -> name RejoinPastMembers
# Run: /PyScriptForm/RejoinPastMembers
#
# Admin only. Current roster rows are skipped (including Inactive).
# Deceased and archived people are listed so you can leave them unchecked.
# Does not restore pending, notes, grade, shirt size, or registration answers.
# Does not send email.
#
# IronPython notes (TouchPoint embeds IronPython 2.7):
#   - Use print without parentheses; except Exception, ex
#   - Put UI in model.Form on GET (PyScriptForm ignores Output)
#   - SQL params via model.DynamicData()
#   - model.ExecuteSql is debug-only, so enrollment date and extra values
#     are written through a writable CMSDataContext. Join and subgroups use
#     model.JoinOrg and model.AddSubGroup.

import traceback

SCRIPT_PATH = '/PyScriptForm/RejoinPastMembers'

BRAND = {
    'black-pearl': '#001429',
    'downriver': '#012B58',
    'azure': '#019CFF',
    'hawkes': '#CCEBFF',
    'linen': '#F5F4E8',
    'forest': '#005C3B',
    'deep-copper': '#801D13',
    'vermillion': '#E52300',
    'crusta': '#FF7941',
}


def _is_null(val):
    if val is None:
        return True
    try:
        from System import DBNull
        if val is DBNull.Value:
            return True
    except:
        pass
    return False


def _s(val, default=''):
    if _is_null(val):
        return default
    try:
        s = unicode(val).strip()
    except:
        try:
            s = str(val).strip()
        except:
            return default
    if s == '' or s == 'None' or s == 'null':
        return default
    return s


def _i(val, default=0):
    s = _s(val)
    if not s:
        return default
    try:
        return int(s)
    except:
        try:
            return int(float(s))
        except:
            return default


def _flag(val):
    if val is True:
        return True
    s = _s(val).lower()
    return s in ('1', 'true', 'yes')


def _html(val):
    s = _s(val)
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def _get(name, default=None):
    try:
        v = Data.GetValue(name)
    except:
        v = None
    if _is_null(v):
        return default
    return v


def _form_val(name, default=''):
    v = _get(name, None)
    if v is None:
        return default
    return _s(v, default)


def _is_admin():
    try:
        return bool(model.UserIsInRole('Admin'))
    except:
        return False


def _is_post():
    try:
        return _s(model.HttpMethod).lower() == 'post'
    except:
        return False


def _dd():
    return model.DynamicData()


def _ex_msg(ex):
    try:
        msg = _s(ex.Message)
        if msg:
            return msg
    except:
        pass
    return _s(ex)


def _parse_date(text):
    s = _s(text)
    if not s:
        return None
    try:
        from System import DateTime
        return DateTime.Parse(s).Date
    except:
        return None


def _date_s(val):
    if _is_null(val):
        return ''
    try:
        return val.ToString('yyyy-MM-dd')
    except:
        s = _s(val)
        if len(s) >= 10:
            return s[:10]
        return s


def _as_datetime(val):
    if _is_null(val):
        return None
    try:
        from System import DateTime
        if isinstance(val, DateTime):
            return val
    except:
        pass
    try:
        from System import DateTime
        return DateTime.Parse(_s(val))
    except:
        return None


def _row(row, name, default=None):
    try:
        v = getattr(row, name)
    except:
        return default
    if _is_null(v):
        return default
    return v


def _group_names(text):
    names = []
    seen = {}
    raw = _s(text).replace('\r\n', '\n').replace('\r', '\n')
    for part in raw.split('\n'):
        name = part.strip()
        if not name or name in seen:
            continue
        seen[name] = 1
        names.append(name)
    return names


def _selected_ids():
    raw = _s(_get('peopleids', ''))
    ids = []
    seen = {}
    for part in raw.replace(';', ',').split(','):
        pid = _i(part, 0)
        if pid > 0 and pid not in seen:
            seen[pid] = 1
            ids.append(pid)
    return ids


def _styles():
    css = """
<style>
.rj-root { max-width: 1100px; margin: 0 auto; padding: 16px 20px 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: {{black-pearl}}; background: #f5f5f5; box-sizing: border-box; }
.rj-root * { box-sizing: border-box; }
.rj-head { background: {{downriver}}; color: #fff; border-radius: 10px; padding: 18px 20px; margin-bottom: 16px; }
.rj-head h1 { margin: 0 0 6px; font-size: 22px; font-weight: 650; }
.rj-head p { margin: 0; font-size: 14px; line-height: 1.45; color: {{hawkes}}; }
.rj-card { background: #fff; border: 1px solid #e4e2d6; border-radius: 10px; padding: 16px 18px; margin-bottom: 14px; }
.rj-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
.rj-field { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.rj-field input { font: inherit; color: {{black-pearl}}; border: 1px solid #cfcabb; border-radius: 6px; padding: 7px 9px; min-width: 11em; }
.rj-actions { display: flex; gap: 8px; align-items: center; }
.rj-btn { font: inherit; border: 0; border-radius: 999px; padding: 8px 16px; cursor: pointer; }
.rj-btn-primary { background: {{downriver}}; color: #fff; }
.rj-btn-go { background: {{forest}}; color: #fff; }
.rj-note { border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 14px; }
.rj-note.ok { background: #e7f5ee; color: {{forest}}; }
.rj-note.bad { background: #fdecea; color: {{deep-copper}}; }
.rj-meta { font-size: 14px; margin: 0 0 10px; }
.rj-meta a { color: {{azure}}; }
.rj-table-wrap { overflow-x: auto; }
table.rj { width: 100%; border-collapse: collapse; font-size: 14px; }
table.rj th, table.rj td { text-align: left; padding: 8px 8px; border-bottom: 1px solid #eee; vertical-align: top; }
table.rj th { font-size: 12px; letter-spacing: .02em; color: {{downriver}}; }
table.rj a { color: {{azure}}; text-decoration: none; }
.rj-pill { display: inline-block; border-radius: 999px; padding: 1px 7px; font-size: 11px; margin-left: 4px; }
.rj-pill.dead { background: #fdecea; color: {{vermillion}}; }
.rj-pill.arch { background: {{linen}}; color: {{crusta}}; }
.rj-pill.lead { background: {{hawkes}}; color: {{downriver}}; }
.rj-muted { color: #667; }
.rj-results li { margin: 4px 0; }
</style>
"""
    for key in BRAND.keys():
        css = css.replace('{{' + key + '}}', BRAND[key])
    return css


def _search_sql():
    # A drop overlaps the range when they had started by the end date and
    # left on or after the start date. Latest overlapping drop wins.
    # TransactionStatus 0 = not voided. Type 5 = drop.
    return """
;WITH drops AS (
    SELECT
        et.TransactionId,
        et.PeopleId,
        et.MemberTypeId,
        et.TransactionDate AS DropDate,
        et.SmallGroups,
        COALESCE(et.EnrollmentDate, prior.PriorEnrollDate) AS EnrollmentDate,
        ROW_NUMBER() OVER (
            PARTITION BY et.PeopleId
            ORDER BY et.TransactionDate DESC, et.TransactionId DESC
        ) AS rn
    FROM dbo.EnrollmentTransaction et
    OUTER APPLY (
        SELECT TOP 1 COALESCE(j.EnrollmentDate, j.TransactionDate) AS PriorEnrollDate
        FROM dbo.EnrollmentTransaction j
        WHERE j.OrganizationId = et.OrganizationId
          AND j.PeopleId = et.PeopleId
          AND j.TransactionTypeId = 1
          AND ISNULL(j.TransactionStatus, 0) = 0
          AND j.TransactionDate <= et.TransactionDate
        ORDER BY j.TransactionDate DESC, j.TransactionId DESC
    ) prior
    WHERE et.OrganizationId = CAST(@OrgId AS int)
      AND et.TransactionTypeId = 5
      AND ISNULL(et.TransactionStatus, 0) = 0
      AND CONVERT(date, et.TransactionDate) >= CONVERT(date, @StartDate)
      AND CONVERT(date, COALESCE(et.EnrollmentDate, prior.PriorEnrollDate, et.TransactionDate))
            <= CONVERT(date, @EndDate)
)
SELECT
    d.TransactionId,
    d.PeopleId,
    COALESCE(NULLIF(LTRIM(RTRIM(p.Name2)), ''), p.Name, '(unknown)') AS PersonName,
    CASE WHEN ISNULL(p.IsDeceased, 0) = 1 OR p.DeceasedDate IS NOT NULL THEN 1 ELSE 0 END AS IsDeceased,
    CASE WHEN ISNULL(p.ArchivedFlag, 0) = 1 THEN 1 ELSE 0 END AS IsArchived,
    d.MemberTypeId,
    mt.Description AS MemberType,
    ISNULL(mt.AttendanceTypeId, 0) AS AttendanceTypeId,
    d.EnrollmentDate,
    d.DropDate,
    d.SmallGroups,
    (
        SELECT COUNT(*)
        FROM dbo.PrevOrgMemberExtra ev
        WHERE ev.EnrollmentTranId = d.TransactionId
    ) AS ExtraCount
FROM drops d
JOIN dbo.People p ON p.PeopleId = d.PeopleId
LEFT JOIN lookup.MemberType mt ON mt.Id = d.MemberTypeId
WHERE d.rn = 1
  AND NOT EXISTS (
        SELECT 1
        FROM dbo.OrganizationMembers om
        WHERE om.OrganizationId = CAST(@OrgId AS int)
          AND om.PeopleId = d.PeopleId
  )
ORDER BY PersonName, d.PeopleId
"""


def _sql_params(org_id, start, end):
    p = _dd()
    p.AddValue('OrgId', str(org_id))
    p.AddValue('StartDate', start.ToString('yyyy-MM-dd'))
    p.AddValue('EndDate', end.ToString('yyyy-MM-dd'))
    return p


def _load_org(org_id):
    sql = """
SELECT TOP 1 o.OrganizationId, o.OrganizationName
FROM dbo.Organizations o
WHERE o.OrganizationId = CAST(@OrgId AS int)
"""
    p = _dd()
    p.AddValue('OrgId', str(org_id))
    rows = list(q.QuerySql(sql, p))
    if not rows:
        return None
    return rows[0]


def _search(org_id, start, end):
    return list(q.QuerySql(_search_sql(), _sql_params(org_id, start, end)))


def _writable_db():
    """Writable church database. model.ExecuteSql only runs when TouchPoint is in debug."""
    from System import Array, Object, Type
    from System.Reflection import BindingFlags
    t = Type.GetType('CmsData.CMSDataContext, CmsData')
    if t is None:
        try:
            import clr
            clr.AddReference('CmsData')
        except:
            pass
        t = Type.GetType('CmsData.CMSDataContext, CmsData')
    if t is None:
        raise Exception('Could not load CMSDataContext.')
    host = _s(model.DatabaseName)
    if not host:
        raise Exception('Could not read the church database name.')
    flags = BindingFlags.Public | BindingFlags.Static
    chosen = None
    for m in t.GetMethods(flags):
        if m.Name != 'Create':
            continue
        ps = m.GetParameters()
        if len(ps) == 2 and _s(ps[1].ParameterType.FullName) == 'System.Boolean':
            chosen = m
            break
    if chosen is None:
        raise Exception('Could not find CMSDataContext.Create.')
    args = Array[Object]([host, False])
    db = chosen.Invoke(None, args)
    if db is None:
        raise Exception('Could not open a writable database connection.')
    return db


def _scalar_int(db, sql, a, b):
    from System import Array, Int32, Object
    method = None
    bt = db.GetType()
    while bt is not None and method is None:
        for m in bt.GetMethods():
            if m.Name != 'ExecuteQuery' or not m.IsGenericMethodDefinition:
                continue
            if len(m.GetParameters()) == 2:
                method = m
                break
        bt = bt.BaseType
    if method is None:
        raise Exception('Could not query OrganizationMembers.')
    generic = method.MakeGenericMethod(Int32)
    packed = Array[Object]([a, b])
    rows = generic.Invoke(db, Array[Object]([sql, packed]))
    for n in rows:
        return int(n)
    return 0


def _member_count(db, org_id, people_id):
    sql = "SELECT COUNT(*) FROM dbo.OrganizationMembers WHERE OrganizationId = {0} AND PeopleId = {1}"
    return _scalar_int(db, sql, int(org_id), int(people_id))


def _apply_type_and_date(db, org_id, people_id, member_type_id, enroll):
    if enroll is None and member_type_id <= 0:
        return 'left enrollment date and member type as the new join'
    if enroll is not None and member_type_id > 0:
        db.ExecuteCommand(
            "UPDATE dbo.OrganizationMembers SET EnrollmentDate = {0}, MemberTypeId = {1} "
            "WHERE OrganizationId = {2} AND PeopleId = {3}",
            enroll, int(member_type_id), int(org_id), int(people_id))
        return ''
    if enroll is not None:
        db.ExecuteCommand(
            "UPDATE dbo.OrganizationMembers SET EnrollmentDate = {0} "
            "WHERE OrganizationId = {1} AND PeopleId = {2}",
            enroll, int(org_id), int(people_id))
        return 'member type was missing, left as Member'
    db.ExecuteCommand(
        "UPDATE dbo.OrganizationMembers SET MemberTypeId = {0} "
        "WHERE OrganizationId = {1} AND PeopleId = {2}",
        int(member_type_id), int(org_id), int(people_id))
    return 'original enrollment date was missing, left as today'


def _restore_groups(org_id, people_id, names):
    added = 0
    failed = []
    for name in names:
        try:
            model.AddSubGroup(int(people_id), int(org_id), name)
            added += 1
        except Exception, ex:
            failed.append(name + ' (' + _ex_msg(ex) + ')')
    return added, failed


def _restore_extras(db, org_id, people_id, tran_id):
    # Type is computed. Copy the drop's member extra values onto the new row.
    sql = """
DECLARE @oid int = {0}, @pid int = {1}, @tran int = {2};
INSERT INTO dbo.OrgMemberExtra
    (OrganizationId, PeopleId, Field, Data, DataType, StrValue, DateValue, IntValue, BitValue, TransactionTime, UseAllValues)
SELECT @oid, @pid, src.Field, src.Data, src.DataType, src.StrValue, src.DateValue, src.IntValue, src.BitValue, src.TransactionTime, src.UseAllValues
FROM dbo.PrevOrgMemberExtra src
WHERE src.EnrollmentTranId = @tran
  AND src.Field IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM dbo.OrgMemberExtra cur
        WHERE cur.OrganizationId = @oid
          AND cur.PeopleId = @pid
          AND cur.Field = src.Field
  )
"""
    return int(db.ExecuteCommand(sql, int(org_id), int(people_id), int(tran_id)))


def _rejoin_one(db, org_id, row):
    pid = _i(_row(row, 'PeopleId'), 0)
    tran_id = _i(_row(row, 'TransactionId'), 0)
    type_id = _i(_row(row, 'MemberTypeId'), 0)
    enroll = _as_datetime(_row(row, 'EnrollmentDate'))
    names = _group_names(_row(row, 'SmallGroups', ''))
    if pid <= 0 or tran_id <= 0:
        return False, 'Missing people id or drop record.'
    if _member_count(db, org_id, pid) > 0:
        return False, 'Already on the roster. Skipped.'
    model.JoinOrg(int(org_id), int(pid))
    if _member_count(db, org_id, pid) < 1:
        return False, 'Join did not create a membership.'
    note = _apply_type_and_date(db, org_id, pid, type_id, enroll)
    added, failed = _restore_groups(org_id, pid, names)
    extras = _restore_extras(db, org_id, pid, tran_id)
    bits = []
    bits.append(_s(_row(row, 'MemberType'), 'Member'))
    if enroll is not None:
        bits.append('enrolled ' + _date_s(enroll))
    bits.append(str(added) + ' subgroup' + ('' if added == 1 else 's'))
    bits.append(str(extras) + ' extra value' + ('' if extras == 1 else 's'))
    if note:
        bits.append(note)
    if failed:
        bits.append('subgroup problem: ' + '; '.join(failed))
    return True, ', '.join(bits)


def _rejoin(db, org_id, rows, selected):
    by_id = {}
    for row in rows:
        pid = _i(_row(row, 'PeopleId'), 0)
        if pid > 0:
            by_id[pid] = row
    ok = []
    bad = []
    for pid in selected:
        row = by_id.get(pid)
        if row is None:
            bad.append((str(pid), 'Not in this preview (already on the roster, or outside the date range).'))
            continue
        name = _s(_row(row, 'PersonName'), str(pid))
        try:
            success, detail = _rejoin_one(db, org_id, row)
        except Exception, ex:
            success = False
            detail = _ex_msg(ex)
        if success:
            ok.append((name, detail))
        else:
            bad.append((name, detail))
    return ok, bad


def _banner(ok, bad):
    html = ''
    if ok:
        html += '<div class="rj-note ok">Re-joined ' + str(len(ok)) + '.</div><ul class="rj-results">'
        for name, detail in ok:
            html += '<li>' + _html(name) + ' <span class="rj-muted">(' + _html(detail) + ')</span></li>'
        html += '</ul>'
    if bad:
        html += '<div class="rj-note bad">Could not re-join ' + str(len(bad)) + '.</div><ul class="rj-results">'
        for name, detail in bad:
            html += '<li>' + _html(name) + ' <span class="rj-muted">(' + _html(detail) + ')</span></li>'
        html += '</ul>'
    return html


def _pills(row):
    html = ''
    if _flag(_row(row, 'IsDeceased')):
        html += '<span class="rj-pill dead">Deceased</span>'
    if _flag(_row(row, 'IsArchived')):
        html += '<span class="rj-pill arch">Archived</span>'
    if _i(_row(row, 'AttendanceTypeId'), 0) == 10:
        html += '<span class="rj-pill lead">Leader</span>'
    return html


def _table(rows):
    if not rows:
        return '<p class="rj-meta">No past members were enrolled in this involvement during that range. People already on the roster are not listed.</p>'
    html = '<p class="rj-meta">' + str(len(rows)) + ' past member' + ('' if len(rows) == 1 else 's') + '. Check the people to add back, then re-join. Deceased and archived people are included so you can leave them unchecked.</p>'
    html += '<div class="rj-table-wrap"><table class="rj"><thead><tr>'
    html += '<th><input type="checkbox" id="rj-all" onclick="rjAll(this)" title="Select all" /></th>'
    html += '<th>Name</th><th>People ID</th><th>Member type</th><th>Enrolled</th><th>Dropped</th><th>Subgroups</th><th>Extras</th>'
    html += '</tr></thead><tbody>'
    for row in rows:
        pid = _i(_row(row, 'PeopleId'), 0)
        names = _group_names(_row(row, 'SmallGroups', ''))
        groups = ', '.join(names)
        if len(groups) > 120:
            groups = groups[:117] + '...'
        html += '<tr>'
        html += '<td><input class="rj-pid" type="checkbox" name="peopleids" value="' + str(pid) + '" /></td>'
        html += '<td><a href="/Person2/' + str(pid) + '" target="_blank" rel="noopener">' + _html(_row(row, 'PersonName')) + '</a>' + _pills(row) + '</td>'
        html += '<td>' + str(pid) + '</td>'
        html += '<td>' + _html(_row(row, 'MemberType', '')) + '</td>'
        html += '<td>' + _html(_date_s(_row(row, 'EnrollmentDate'))) + '</td>'
        html += '<td>' + _html(_date_s(_row(row, 'DropDate'))) + '</td>'
        html += '<td>' + (_html(groups) if groups else '<span class="rj-muted">—</span>') + '</td>'
        html += '<td>' + str(_i(_row(row, 'ExtraCount'), 0)) + '</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    html += '<div class="rj-actions" style="margin-top:12px">'
    html += '<button type="submit" class="rj-btn rj-btn-go" onclick="return rjRejoin();">Re-join selected</button>'
    html += '</div>'
    return html


def _script():
    return """
<script>
function rjAll(src) {
  var boxes = document.getElementsByClassName('rj-pid');
  for (var i = 0; i < boxes.length; i++) boxes[i].checked = src.checked;
}
function rjRejoin() {
  var boxes = document.getElementsByClassName('rj-pid');
  var n = 0;
  for (var i = 0; i < boxes.length; i++) if (boxes[i].checked) n++;
  if (!n) { alert('Select at least one person.'); return false; }
  document.getElementById('rj-action').value = 'rejoin';
  return confirm('Re-join ' + n + ' selected people? They will be added back with the member type, subgroups, extra values, and enrollment date from the drop that overlapped this range.');
}
</script>
"""


def _page(org_id, start_s, end_s, org_row, rows, notice, error):
    html = _styles()
    html += '<div class="rj-root">'
    html += '<div class="rj-head"><h1>Re-join past members</h1>'
    html += '<p>Enter an involvement number and the dates someone was enrolled. '
    html += 'People who dropped during that range are included. '
    html += 'Re-join puts back the member type, subgroups, and member extra values from that drop, and sets the enrollment date back to the original one. '
    html += 'Pending, notes, grade, shirt size, and registration answers stay off. Nobody is emailed.</p></div>'
    html += '<form method="post" action="' + SCRIPT_PATH + '">'
    html += '<input type="hidden" name="action" id="rj-action" value="preview" />'
    html += '<div class="rj-card"><div class="rj-row">'
    html += '<label class="rj-field">Involvement #<input name="OrgId" type="number" min="1" required value="' + _html(org_id if org_id else '') + '" /></label>'
    html += '<label class="rj-field">From<input name="StartDate" type="date" required value="' + _html(start_s) + '" /></label>'
    html += '<label class="rj-field">Through<input name="EndDate" type="date" required value="' + _html(end_s) + '" /></label>'
    html += '<div class="rj-actions"><button type="submit" class="rj-btn rj-btn-primary" onclick="document.getElementById(\'rj-action\').value=\'preview\';">Preview</button></div>'
    html += '</div></div>'
    if error:
        html += '<div class="rj-note bad">' + _html(error) + '</div>'
    if notice:
        html += notice
    if org_row is not None and rows is not None:
        oid = _i(_row(org_row, 'OrganizationId'), 0)
        html += '<div class="rj-card">'
        html += '<p class="rj-meta"><a href="/Org/' + str(oid) + '" target="_blank" rel="noopener">' + _html(_row(org_row, 'OrganizationName')) + '</a> (#' + str(oid) + ')</p>'
        html += _table(rows)
        html += '</div>'
    html += '</form>'
    html += _script()
    html += '</div>'
    return html


def _show(html):
    if _is_post():
        print html
    else:
        model.Form = html


def _error_page(ex):
    html = _styles()
    html += '<div class="rj-root"><div class="rj-head"><h1>Re-join past members</h1>'
    html += '<p>The page failed before it could finish.</p></div>'
    html += '<div class="rj-card"><pre style="white-space:pre-wrap;font-size:12px">'
    try:
        html += _html(traceback.format_exc())
    except:
        html += _html(_ex_msg(ex))
    html += '</pre></div></div>'
    return html


model.Header = 'Re-join Past Members'
model.Title = 'Re-join Past Members'

try:
    if not _is_admin():
        _show(_styles() + '<div class="rj-root"><div class="rj-note bad">Admin role required.</div></div>')
    else:
        org_text = _form_val('OrgId')
        start_s = _form_val('StartDate')
        end_s = _form_val('EndDate')
        action = _form_val('action')
        org_id = _i(org_text, 0)
        org_row = None
        rows = None
        notice = ''
        error = ''
        if _is_post() and (action == 'preview' or action == 'rejoin'):
            start = _parse_date(start_s)
            end = _parse_date(end_s)
            if org_id <= 0:
                error = 'Enter an involvement number.'
            elif start is None or end is None:
                error = 'Enter a from date and a through date.'
            elif start > end:
                error = 'The from date has to be on or before the through date.'
            else:
                org_row = _load_org(org_id)
                if org_row is None:
                    error = 'No involvement with that number.'
                else:
                    rows = _search(org_id, start, end)
                    if action == 'rejoin':
                        selected = _selected_ids()
                        if not selected:
                            error = 'Select at least one person.'
                        else:
                            db = None
                            try:
                                db = _writable_db()
                                ok, bad = _rejoin(db, org_id, rows, selected)
                                notice = _banner(ok, bad)
                                rows = _search(org_id, start, end)
                            finally:
                                if db is not None:
                                    db.Dispose()
        _show(_page(org_text, start_s, end_s, org_row, rows, notice, error))
except Exception, ex:
    _show(_error_page(ex))
