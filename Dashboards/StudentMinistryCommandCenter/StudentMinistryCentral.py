#Roles=Access
# Script: StudentMinistryCentral.py
# Purpose: Refuge / Student Ministry command center. Home (attendance, FY
#   events, decisions, baptisms, leader tiles), Volunteers, Demographics,
#   Ministry outcomes, and Small Groups (VBS-style assign). Event detail
#   launches Involvement Dashboard; volunteer intake launches Onboarding.
# Author: Jake Pierson
# Date: 2026-09-21
#
# Install: Special Content -> Python Scripts -> name StudentMinistryCentral
# Run: /PyScriptForm/StudentMinistryCentral
# Config: Special Content -> Text -> StudentMinistryCentralConfig
#
# IronPython notes (TouchPoint embeds IronPython 2.7):
#   - print without parentheses; except Exception, ex
#   - Put UI in model.Form on GET (PyScriptForm ignores Output)
#   - Prefer model.DynamicData() for SQL params
#   - Prefer token replace / concat over .format() for large HTML
#   - No f-strings, no pathlib, no requests

import datetime
import json
import traceback

try:
    import sys
    reload(sys)
    sys.setdefaultencoding('latin-1')
except:
    pass

APP_TITLE = 'Student Ministry Command Center'
CONFIG_CONTENT_NAME = 'StudentMinistryCentralConfig'
SCRIPT_FALLBACK = 'StudentMinistryCentral'
HEADER_LOGO_URL = (
    'https://irp.cdn-website.com/395ab2a8/dms3rep/multi/opt/RefugeStudents-logos-40-1920w.png'
)

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

NAV_SEGMENTS = [
    ('', [('home', 'Home')]),
    ('People', [('volunteers', 'Volunteers'), ('demographics', 'Demographics')]),
    ('Ministry', [('ministry', 'Ministry'), ('groups', 'Small Groups')]),
    ('Admin', [('config', 'Config')]),
]

TITLE_MAP = {
    'home': 'Home',
    'volunteers': 'Volunteers',
    'demographics': 'Demographics',
    'ministry': 'Ministry',
    'groups': 'Small Groups',
    'config': 'Config',
}

_CONFIG_LOAD_INFO = ''
_LOAD_WARNINGS = []
_KEYWORD_CACHE = {}


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


def _b(val):
    return _s(val).lower() in ('1', 'true', 'yes', 'on')


def _html(val):
    s = _s(val)
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('"', '&quot;')
    return s


def _ex_msg(ex):
    try:
        return _s(ex.ToString()) or str(ex)
    except:
        try:
            return str(ex)
        except:
            return 'Unknown error'


def _dd():
    return model.DynamicData()


def _warn(msg):
    _LOAD_WARNINGS.append(_s(msg))


def _script_path():
    name = ''
    try:
        name = _s(model.ScriptName)
    except:
        name = ''
    if not name:
        name = SCRIPT_FALLBACK
    try:
        enc = model.UrlEncode(name).replace('+', '%20')
    except:
        enc = name.replace(' ', '%20')
    return '/PyScriptForm/' + enc


def _form_val(name, default=''):
    try:
        if model.DataHas(name):
            return _s(model.Dictionary(name), default)
    except:
        pass
    try:
        from System.Web import HttpContext
        req = HttpContext.Current.Request
        if req.Form is not None and req.Form[name] is not None:
            return _s(req.Form[name], default)
        if req.QueryString is not None and req.QueryString[name] is not None:
            return _s(req.QueryString[name], default)
    except:
        pass
    try:
        v = Data.GetValue(name)
        if not _is_null(v):
            return _s(v, default)
    except:
        pass
    return default


def _show(html):
    if model.HttpMethod == 'get':
        model.Form = html
    else:
        print html


def _redirect(msg='', view=''):
    qs = []
    if view:
        qs.append('view=' + view)
    if msg:
        qs.append('msg=' + model.UrlEncode(msg))
    url = _script_path()
    if qs:
        url = url + '?' + '&'.join(qs)
    print 'REDIRECT=' + url


def _json_out(obj):
    print json.dumps(obj)


def _today():
    return datetime.date.today()


def _ymd(d):
    if d is None:
        return ''
    try:
        return d.strftime('%Y-%m-%d')
    except:
        return _s(d)[:10]


def _parse_date(val):
    if _is_null(val):
        return None
    try:
        if hasattr(val, 'Year') and hasattr(val, 'Month'):
            return datetime.date(int(val.Year), int(val.Month), int(val.Day))
    except:
        pass
    s = _s(val)
    if len(s) >= 10:
        try:
            return datetime.datetime.strptime(s[:10], '%Y-%m-%d').date()
        except:
            return None
    return None


def _fy_bounds(d=None):
    """July 1 – June 30. End is exclusive (next July 1)."""
    if d is None:
        d = _today()
    if d.month >= 7:
        start = datetime.date(d.year, 7, 1)
    else:
        start = datetime.date(d.year - 1, 7, 1)
    end = datetime.date(start.year + 1, 7, 1)
    return start, end


def _week_start(d, dow):
    """dow: 0=Monday … 6=Sunday (datetime.weekday)."""
    dow = _i(dow, 2)
    if dow < 0 or dow > 6:
        dow = 2
    delta = (d.weekday() - dow) % 7
    return d - datetime.timedelta(days=delta)


def _add_days(d, n):
    return d + datetime.timedelta(days=_i(n))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _default_config():
    return {
        'version': 1,
        'ms_orgid': 0,
        'hs_orgid': 0,
        'week_start_dow': 2,
        'event_program_id': 0,
        'event_division_ids': '',
        'leaders_orgid': 0,
        'student_leaders_orgid': 0,
        'coaches_orgid': 0,
        'onboarding_url': '/PyScriptForm/VolunteerOnboardingDashboard',
        'involvement_dash_url': '/PyScriptForm/InvolvementDashboard',
        'kw_decision': 'Decision to Follow Jesus',
        'kw_decision_scope': 'Refuge Student Ministry',
        'kw_stories': 'Stories of Transformation',
        'baptism_scope': 'standing',
        'kids_program_id': 0,
        'awana_program_id': 0,
        'senior_year_orgid': 0,
        'volunteer_program_id': 0,
        'volunteer_extra_orgids': '',
        'view_only_role': '',
        'small_group_names': '',
        'header_logo_url': HEADER_LOGO_URL,
    }


def _parse_id_list(raw):
    out = []
    seen = {}
    for part in _s(raw).replace(';', ',').split(','):
        n = _i(part, 0)
        if n > 0 and n not in seen:
            seen[n] = True
            out.append(n)
    return out


def _content_body_as_text(val):
    if val is None:
        return ''
    try:
        from System import DBNull
        if val is DBNull.Value:
            return ''
    except:
        pass
    try:
        return unicode(val)
    except:
        try:
            return str(val)
        except:
            return ''


def _raw_content_text(name):
    name = _s(name)
    if not name:
        return ''
    try:
        body = _content_body_as_text(model.TextContent(name)).strip()
        if body:
            return body
    except:
        pass
    sql = """
SELECT TOP 1 c.Body
FROM dbo.Content c
WHERE LTRIM(RTRIM(c.Name)) = @name
ORDER BY CASE c.TypeID WHEN 1 THEN 0 WHEN 2 THEN 1 ELSE 2 END, c.Id DESC
"""
    p = _dd()
    p.AddValue('name', name)
    try:
        rows = list(q.QuerySql(sql, p))
        if rows:
            body = _content_body_as_text(rows[0].Body).strip()
            if body:
                return body
    except:
        pass
    return ''


def _load_config():
    global _CONFIG_LOAD_INFO
    cfg = _default_config()
    raw = _raw_content_text(CONFIG_CONTENT_NAME)
    if not raw:
        _CONFIG_LOAD_INFO = 'store empty — using script defaults'
        return cfg
    parsed = None
    status = ''
    try:
        parsed = json.loads(raw)
        status = 'ok:json'
    except Exception, ex:
        status = 'json fail: ' + _s(ex)[:60]
        try:
            import clr
            clr.AddReference('System.Web.Extensions')
            from System.Web.Script.Serialization import JavaScriptSerializer
            ser = JavaScriptSerializer()
            parsed = ser.DeserializeObject(raw)
            status = 'ok:javascriptserializer'
        except Exception, ex2:
            status = status + ' / js: ' + _s(ex2)[:40]
            parsed = None
    if isinstance(parsed, dict):
        for k in cfg.keys():
            if k in parsed:
                cfg[k] = parsed[k]
        _CONFIG_LOAD_INFO = status + ' · ' + str(len(raw)) + ' chars'
    else:
        _CONFIG_LOAD_INFO = status + ' · defaults only'
    return cfg


def _save_config(cfg):
    text = json.dumps(cfg, indent=2)
    model.WriteContentText(CONFIG_CONTENT_NAME, text)
    return text


def _cfg_i(cfg, key):
    return _i((cfg or {}).get(key), 0)


def _standing_orgs(cfg):
    out = []
    for key in ('ms_orgid', 'hs_orgid'):
        n = _cfg_i(cfg, key)
        if n > 0:
            out.append(n)
    return out


def _leader_orgs(cfg):
    out = []
    for key in ('leaders_orgid', 'student_leaders_orgid', 'coaches_orgid'):
        n = _cfg_i(cfg, key)
        if n > 0:
            out.append(n)
    return out


def _exclude_orgs(cfg):
    seen = {}
    out = []
    for n in _standing_orgs(cfg) + _leader_orgs(cfg):
        if n not in seen:
            seen[n] = True
            out.append(n)
    return out


def _group_name_list(cfg):
    names = []
    seen = {}
    for part in _s(cfg.get('small_group_names')).split(','):
        part = part.strip()
        if part and part.lower() not in seen:
            seen[part.lower()] = True
            names.append(part)
    return names


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _is_admin():
    try:
        return bool(model.UserIsInRole('Admin'))
    except:
        return False


def _in_role(name):
    name = _s(name)
    if not name:
        return False
    try:
        return bool(model.UserIsInRole(name))
    except:
        return False


def _can_access(cfg):
    if _is_admin():
        return True
    staff = _in_role('Staff') or _in_role('Elders')
    return staff and _in_role('Next Gen')


def _is_view_only(cfg):
    if _is_admin():
        return False
    role = _s(cfg.get('view_only_role'))
    return bool(role) and _in_role(role)


def _can_write(cfg):
    return _can_access(cfg) and not _is_view_only(cfg)


def _resolve_view(cfg):
    view = _s(_form_val('view', '')).lower()
    if view not in TITLE_MAP:
        view = 'home'
    if view == 'config' and not _is_admin():
        view = 'home'
    if not _can_access(cfg):
        view = 'home'
    return view


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def _sql_in_int(ids, prefix):
    """Return (sql_fragment, params_dict_values already added to p). Caller adds values."""
    ids = [n for n in (ids or []) if _i(n) > 0]
    if not ids:
        return 'NULL', []
    parts = []
    names = []
    i = 0
    while i < len(ids):
        nm = prefix + str(i)
        parts.append('@' + nm)
        names.append((nm, ids[i]))
        i += 1
    return ','.join(parts), names


def _bind_ids(p, names):
    for nm, val in names:
        p.AddValue(nm, val)


def _person_row(r):
    return {
        'people_id': _i(r.PeopleId),
        'name': _s(r.PersonName, '(Unknown)'),
        'first': _s(r.FirstName) if hasattr(r, 'FirstName') else '',
        'last': _s(r.LastName) if hasattr(r, 'LastName') else '',
        'age': _i(r.Age) if hasattr(r, 'Age') and not _is_null(r.Age) else '',
        'grade': _s(r.GradeLabel) if hasattr(r, 'GradeLabel') else '',
        'gender': _s(r.GenderLabel) if hasattr(r, 'GenderLabel') else '',
        'school': _s(r.SchoolOther) if hasattr(r, 'SchoolOther') else '',
        'groups': _s(r.GroupNames) if hasattr(r, 'GroupNames') else '',
        'org_id': _i(r.OrganizationId) if hasattr(r, 'OrganizationId') else 0,
        'org_name': _s(r.OrganizationName) if hasattr(r, 'OrganizationName') else '',
        'extra': _s(r.Extra) if hasattr(r, 'Extra') else '',
    }


def _sql_person_select():
    return """
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName,
    pe.LastName,
    pe.Age,
    ISNULL(pe.SchoolOther, '') AS SchoolOther,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    COALESCE(
        NULLIF(LTRIM(RTRIM(gl_om.Description)), ''),
        NULLIF(LTRIM(RTRIM(gl_pe.Description)), ''),
        'Unknown'
    ) AS GradeLabel
"""


def _sql_person_joins():
    return """
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl_pe ON pe.GradeLevelId = gl_pe.Id
LEFT JOIN lookup.GradeLevel gl_om ON om.GradeLevelId = gl_om.Id
"""


def _org_members(org_ids, extra_where=''):
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT DISTINCT
""" + _sql_person_select() + """
    , om.OrganizationId
    , o.OrganizationName
    , STUFF((
        SELECT ', ' + mt.Name
        FROM dbo.OrgMemMemTags omt
        INNER JOIN dbo.MemberTags mt ON mt.Id = omt.MemberTagId AND mt.OrgId = omt.OrgId
        WHERE omt.OrgId = om.OrganizationId AND omt.PeopleId = om.PeopleId
        FOR XML PATH(''), TYPE
      ).value('.', 'nvarchar(max)'), 1, 2, '') AS GroupNames
FROM dbo.OrganizationMembers om
INNER JOIN dbo.Organizations o ON o.OrganizationId = om.OrganizationId
""" + _sql_person_joins() + """
WHERE om.OrganizationId IN (""" + frag + """)
  AND ISNULL(pe.IsDeceased, 0) = 0
""" + extra_where + """
ORDER BY PersonName
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('org members: ' + _ex_msg(ex))
        return []
    return [_person_row(r) for r in rows]


def _org_member_count(org_id):
    org_id = _i(org_id)
    if org_id <= 0:
        return 0
    sql = """
SELECT COUNT(*) AS Cnt
FROM dbo.OrganizationMembers om
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
WHERE om.OrganizationId = @oid
  AND ISNULL(pe.IsDeceased, 0) = 0
"""
    p = _dd()
    p.AddValue('oid', org_id)
    try:
        rows = list(q.QuerySql(sql, p))
        if rows:
            return _i(rows[0].Cnt)
    except Exception, ex:
        _warn('member count: ' + _ex_msg(ex))
    return 0


def _keyword_id(desc):
    desc = _s(desc)
    if not desc:
        return 0
    if desc in _KEYWORD_CACHE:
        return _KEYWORD_CACHE[desc]
    sql = """
SELECT TOP 1 KeywordId
FROM dbo.Keyword
WHERE LTRIM(RTRIM(Description)) = @d
  AND ISNULL(IsActive, 1) = 1
"""
    p = _dd()
    p.AddValue('d', desc)
    kid = 0
    try:
        rows = list(q.QuerySql(sql, p))
        if rows:
            kid = _i(rows[0].KeywordId)
    except Exception, ex:
        _warn('keyword ' + desc + ': ' + _ex_msg(ex))
    _KEYWORD_CACHE[desc] = kid
    return kid


def _people_with_keywords(kw_names, fy_only, cfg):
    """People who have one non-archived note containing ALL listed keywords."""
    ids = []
    for name in kw_names:
        kid = _keyword_id(name)
        if kid <= 0:
            return []
        ids.append(kid)
    if not ids:
        return []
    joins = ''
    i = 0
    while i < len(ids):
        joins += ' INNER JOIN dbo.TaskNoteKeyword tnk' + str(i)
        joins += ' ON tnk' + str(i) + '.TaskNoteId = tn.TaskNoteId'
        joins += ' AND tnk' + str(i) + '.KeywordId = @k' + str(i)
        i += 1
    fy_sql = ''
    fy_s, fy_e = _fy_bounds()
    if fy_only:
        fy_sql = ' AND tn.CreatedDate >= @fyS AND tn.CreatedDate < @fyE '
    sql = """
SELECT tn.AboutPersonId AS PeopleId,
       MAX(tn.CreatedDate) AS Extra,
       ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
       pe.FirstName, pe.LastName, pe.Age,
       ISNULL(pe.SchoolOther, '') AS SchoolOther,
       CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
       ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.TaskNote tn
""" + joins + """
INNER JOIN dbo.People pe ON pe.PeopleId = tn.AboutPersonId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE ISNULL(tn.IsArchived, 0) = 0
  AND tn.AboutPersonId IS NOT NULL
  AND ISNULL(pe.IsDeceased, 0) = 0
""" + fy_sql + """
GROUP BY tn.AboutPersonId, pe.Name2, pe.FirstName, pe.LastName, pe.Age,
         pe.SchoolOther, pe.GenderId, gl.Description
ORDER BY PersonName
"""
    p = _dd()
    i = 0
    while i < len(ids):
        p.AddValue('k' + str(i), ids[i])
        i += 1
    if fy_only:
        p.AddValue('fyS', _ymd(fy_s))
        p.AddValue('fyE', _ymd(fy_e))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('notes: ' + _ex_msg(ex))
        return []
    people = []
    for r in rows:
        rec = _person_row(r)
        rec['extra'] = _ymd(_parse_date(r.Extra)) if hasattr(r, 'Extra') else ''
        people.append(rec)
    return people


def _baptism_people(cfg):
    fy_s, fy_e = _fy_bounds()
    org_ids = _standing_orgs(cfg)
    org_sql = ''
    frag, names = _sql_in_int(org_ids, 'oid')
    if org_ids and _s(cfg.get('baptism_scope'), 'standing') == 'standing':
        org_sql = """
  AND EXISTS (
      SELECT 1 FROM dbo.OrganizationMembers om
      WHERE om.PeopleId = pe.PeopleId
        AND om.OrganizationId IN (""" + frag + """)
  )
"""
    sql = """
SELECT pe.PeopleId,
       ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
       pe.FirstName, pe.LastName, pe.Age,
       ISNULL(pe.SchoolOther, '') AS SchoolOther,
       CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
       ISNULL(gl.Description, 'Unknown') AS GradeLabel,
       pe.BaptismDate AS Extra
FROM dbo.People pe
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE pe.BaptismDate >= @fyS AND pe.BaptismDate < @fyE
  AND ISNULL(pe.IsDeceased, 0) = 0
""" + org_sql + """
ORDER BY pe.BaptismDate, PersonName
"""
    p = _dd()
    p.AddValue('fyS', _ymd(fy_s))
    p.AddValue('fyE', _ymd(fy_e))
    if org_sql:
        _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('baptisms: ' + _ex_msg(ex))
        return []
    people = []
    for r in rows:
        rec = _person_row(r)
        rec['extra'] = _ymd(_parse_date(r.Extra))
        people.append(rec)
    return people


def _attend_days(org_ids, start, end):
    """Distinct present PeopleIds per meeting date in [start, end)."""
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids or start is None or end is None:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT CAST(a.MeetingDate AS date) AS MeetDay,
       COUNT(DISTINCT a.PeopleId) AS Cnt
FROM dbo.Attend a
WHERE a.OrganizationId IN (""" + frag + """)
  AND a.AttendanceFlag = 1
  AND a.MeetingDate >= @d1
  AND a.MeetingDate < @d2
GROUP BY CAST(a.MeetingDate AS date)
ORDER BY MeetDay
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('attendance: ' + _ex_msg(ex))
        return []
    out = []
    for r in rows:
        d = _parse_date(r.MeetDay)
        if d:
            out.append({'day': d, 'count': _i(r.Cnt)})
    return out


def _attend_people(org_ids, start, end):
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    ISNULL(pe.SchoolOther, '') AS SchoolOther,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.Attend a
INNER JOIN dbo.People pe ON pe.PeopleId = a.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE a.OrganizationId IN (""" + frag + """)
  AND a.AttendanceFlag = 1
  AND a.MeetingDate >= @d1
  AND a.MeetingDate < @d2
  AND ISNULL(pe.IsDeceased, 0) = 0
ORDER BY PersonName
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('attend people: ' + _ex_msg(ex))
        return []
    return [_person_row(r) for r in rows]


def _week_present_total(days, week_start, week_end):
    """Sum of daily distinct counts in the week. One meeting/week ≈ one day."""
    total = 0
    for row in days:
        d = row.get('day')
        if d and d >= week_start and d < week_end:
            total += _i(row.get('count'))
    return total


def _month_weekly_average(days, year, month, dow):
    """Mean of weekly present totals that fall in this calendar month."""
    first = datetime.date(year, month, 1)
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    weeks = {}
    for row in days:
        d = row.get('day')
        if not d or d < first or d >= nxt:
            continue
        ws = _week_start(d, dow)
        key = _ymd(ws)
        weeks[key] = weeks.get(key, 0) + _i(row.get('count'))
    if not weeks:
        return 0.0, 0
    vals = list(weeks.values())
    avg = float(sum(vals)) / float(len(vals))
    return avg, len(vals)


def _attendance_bundle(cfg):
    orgs = _standing_orgs(cfg)
    dow = _cfg_i(cfg, 'week_start_dow')
    if dow <= 0 and dow != 0:
        dow = 2
    today = _today()
    this_ws = _week_start(today, dow)
    last_ws = _add_days(this_ws, -7)
    ly_ws = _add_days(this_ws, -364)
    lookback = _add_days(this_ws, -400)
    ahead = _add_days(this_ws, 7)
    days = _attend_days(orgs, lookback, ahead)
    this_c = _week_present_total(days, this_ws, _add_days(this_ws, 7))
    last_c = _week_present_total(days, last_ws, this_ws)
    ly_c = _week_present_total(days, ly_ws, _add_days(ly_ws, 7))
    month_days = _attend_days(orgs, datetime.date(today.year - 1, 1, 1), _add_days(today, 32))
    this_avg, this_n = _month_weekly_average(month_days, today.year, today.month, dow)
    prev_m = today.month - 1
    prev_y = today.year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    last_avg, last_n = _month_weekly_average(month_days, prev_y, prev_m, dow)
    ly_avg, ly_n = _month_weekly_average(month_days, today.year - 1, today.month, dow)
    return {
        'this_week': this_c,
        'last_week': last_c,
        'last_year_week': ly_c,
        'wow': this_c - last_c,
        'yoy_week': this_c - ly_c,
        'month_avg': this_avg,
        'last_month_avg': last_avg,
        'last_year_month_avg': ly_avg,
        'month_delta': this_avg - last_avg,
        'month_yoy': this_avg - ly_avg,
        'week_start': this_ws,
        'week_end': _add_days(this_ws, 6),
        'month_weeks': this_n,
        'last_month_weeks': last_n,
        'ly_month_weeks': ly_n,
        'this_week_people': _attend_people(orgs, this_ws, _add_days(this_ws, 7)),
    }


def _event_orgs(cfg):
    prog = _cfg_i(cfg, 'event_program_id')
    if prog <= 0:
        return []
    divs = _parse_id_list(cfg.get('event_division_ids'))
    exclude = _exclude_orgs(cfg)
    sql = """
SELECT o.OrganizationId, o.OrganizationName,
       o.FirstMeetingDate, o.LastMeetingDate, o.CreatedDate,
       ISNULL(o.MemberCount, 0) AS MemberCount,
       ISNULL(o.OrganizationStatusId, 0) AS OrganizationStatusId,
       ISNULL(d.Name, '') AS DivisionName,
       ISNULL(p.Name, '') AS ProgramName
FROM dbo.Organizations o
LEFT JOIN dbo.Division d ON o.DivisionId = d.Id
LEFT JOIN dbo.Program p ON d.ProgId = p.Id
WHERE ISNULL(p.Id, 0) = @prog
"""
    p = _dd()
    p.AddValue('prog', prog)
    if divs:
        frag, names = _sql_in_int(divs, 'div')
        sql += ' AND o.DivisionId IN (' + frag + ') '
        _bind_ids(p, names)
    sql += ' ORDER BY ISNULL(o.FirstMeetingDate, o.CreatedDate), o.OrganizationName'
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('events: ' + _ex_msg(ex))
        return []
    skip = {}
    for n in exclude:
        skip[n] = True
    out = []
    for r in rows:
        oid = _i(r.OrganizationId)
        if oid in skip:
            continue
        start = _parse_date(r.FirstMeetingDate) or _parse_date(r.CreatedDate)
        last = _parse_date(r.LastMeetingDate)
        out.append({
            'id': oid,
            'name': _s(r.OrganizationName),
            'start': start,
            'last': last,
            'member_count': _i(r.MemberCount),
            'division': _s(r.DivisionName),
            'status_id': _i(r.OrganizationStatusId),
        })
    return out


def _event_is_past(ev, today=None):
    if today is None:
        today = _today()
    last = ev.get('last')
    start = ev.get('start')
    if last:
        return last < today
    if start:
        return start < today
    return False


def _fy_events(cfg):
    fy_s, fy_e = _fy_bounds()
    evs = []
    for ev in _event_orgs(cfg):
        start = ev.get('start')
        if start and start >= fy_s and start < fy_e:
            evs.append(ev)
        elif start is None:
            evs.append(ev)
    return evs


def _event_enrollments(cfg, events):
    ids = [ev['id'] for ev in (events or [])]
    if not ids:
        return 0, 0, []
    frag, names = _sql_in_int(ids, 'oid')
    sql = """
SELECT om.PeopleId, om.OrganizationId, o.OrganizationName,
       ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
       pe.FirstName, pe.LastName, pe.Age,
       ISNULL(pe.SchoolOther, '') AS SchoolOther,
       CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
       ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.OrganizationMembers om
INNER JOIN dbo.Organizations o ON o.OrganizationId = om.OrganizationId
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE om.OrganizationId IN (""" + frag + """)
  AND ISNULL(pe.IsDeceased, 0) = 0
ORDER BY PersonName, o.OrganizationName
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('event enroll: ' + _ex_msg(ex))
        return 0, 0, []
    people = []
    seen = {}
    for r in rows:
        rec = _person_row(r)
        rec['extra'] = _s(r.OrganizationName)
        people.append(rec)
        seen[_i(r.PeopleId)] = True
    return len(seen), len(people), people


def _birthday_people(org_ids, month=None):
    if month is None:
        month = _today().month
    people = _org_members(org_ids)
    if not people:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    ISNULL(pe.SchoolOther, '') AS SchoolOther,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel,
    pe.BirthDay, pe.BirthMonth
FROM dbo.OrganizationMembers om
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE om.OrganizationId IN (""" + frag + """)
  AND ISNULL(pe.IsDeceased, 0) = 0
  AND pe.BirthMonth = @m
  AND pe.BirthDay IS NOT NULL
ORDER BY pe.BirthDay, PersonName
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('m', month)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('birthdays: ' + _ex_msg(ex))
        return []
    out = []
    for r in rows:
        rec = _person_row(r)
        rec['extra'] = str(_i(r.BirthMonth)) + '/' + str(_i(r.BirthDay))
        out.append(rec)
    return out


def _people_on_programs(prog_ids):
    prog_ids = [n for n in (prog_ids or []) if _i(n) > 0]
    if not prog_ids:
        return []
    frag, names = _sql_in_int(prog_ids, 'prg')
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    ISNULL(pe.SchoolOther, '') AS SchoolOther,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    COALESCE(
        NULLIF(LTRIM(RTRIM(gl_om.Description)), ''),
        NULLIF(LTRIM(RTRIM(gl_pe.Description)), ''),
        'Unknown'
    ) AS GradeLabel
FROM dbo.OrganizationMembers om
INNER JOIN dbo.Organizations o ON o.OrganizationId = om.OrganizationId
LEFT JOIN dbo.Division d ON o.DivisionId = d.Id
""" + _sql_person_joins() + """
WHERE ISNULL(d.ProgId, 0) IN (""" + frag + """)
  AND ISNULL(pe.IsDeceased, 0) = 0
ORDER BY PersonName
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('program people: ' + _ex_msg(ex))
        return []
    return [_person_row(r) for r in rows]


def _grade_key(label):
    s = _s(label).lower()
    digits = ''
    for ch in s:
        if ch >= '0' and ch <= '9':
            digits += ch
        elif digits:
            break
    if digits:
        n = _i(digits)
        if n >= 6 and n <= 12:
            return n
    return 0


def _serving_outside(cfg):
    standing = _standing_orgs(cfg)
    if not standing:
        return []
    vol_prog = _cfg_i(cfg, 'volunteer_program_id')
    extra = _parse_id_list(cfg.get('volunteer_extra_orgids'))
    if vol_prog <= 0 and not extra:
        return []
    st_frag, st_names = _sql_in_int(standing, 'st')
    extra_sql = ''
    p = _dd()
    _bind_ids(p, st_names)
    if extra:
        ex_frag, ex_names = _sql_in_int(extra, 'ex')
        extra_sql = ' OR om2.OrganizationId IN (' + ex_frag + ') '
        _bind_ids(p, ex_names)
    prog_sql = '1=0'
    if vol_prog > 0:
        prog_sql = 'ISNULL(d2.ProgId, 0) = @vprog'
        p.AddValue('vprog', vol_prog)
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    ISNULL(pe.SchoolOther, '') AS SchoolOther,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.OrganizationMembers om
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
WHERE om.OrganizationId IN (""" + st_frag + """)
  AND ISNULL(pe.IsDeceased, 0) = 0
  AND EXISTS (
      SELECT 1
      FROM dbo.OrganizationMembers om2
      INNER JOIN dbo.Organizations o2 ON o2.OrganizationId = om2.OrganizationId
      LEFT JOIN dbo.Division d2 ON o2.DivisionId = d2.Id
      WHERE om2.PeopleId = om.PeopleId
        AND om2.OrganizationId NOT IN (""" + st_frag + """)
        AND (""" + prog_sql + extra_sql + """)
  )
ORDER BY PersonName
"""
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('serving outside: ' + _ex_msg(ex))
        return []
    return [_person_row(r) for r in rows]


def _discover_subgroups(org_ids):
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT DISTINCT mt.Name
FROM dbo.MemberTags mt
WHERE mt.OrgId IN (""" + frag + """)
  AND LTRIM(RTRIM(ISNULL(mt.Name,''))) <> ''
ORDER BY mt.Name
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('subgroups: ' + _ex_msg(ex))
        return []
    return [_s(r.Name) for r in rows]


def _all_group_names(cfg):
    names = []
    seen = {}
    for n in _group_name_list(cfg) + _discover_subgroups(_standing_orgs(cfg) + _leader_orgs(cfg)):
        key = n.lower()
        if n and key not in seen:
            seen[key] = True
            names.append(n)
    names.sort(key=lambda x: x.lower())
    return names


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _parse_people_ids(raw):
    ids = []
    seen = {}
    for part in _s(raw).replace(';', ',').split(','):
        n = _i(part)
        if n > 0 and n not in seen:
            seen[n] = True
            ids.append(n)
    return ids


def _add_people_to_tag(people_ids_raw, tag_name, clear_first):
    owner_id = 0
    try:
        owner_id = int(model.UserPeopleId)
    except:
        owner_id = 0
    if not owner_id:
        return {'error': 'You must be signed in to add people to a tag.'}
    tag_name = _s(tag_name).replace('!', '_').strip()
    if not tag_name:
        return {'error': 'Tag name is required.'}
    if len(tag_name) > 50:
        return {'error': 'Tag name is too long (max 50 characters).'}
    people_ids = _parse_people_ids(people_ids_raw)
    if not people_ids:
        return {'error': 'No people to add to the tag.'}
    clear = _s(clear_first).lower() in ('1', 'true', 'yes', 'clear')
    query = "peopleids='" + ','.join([str(pid) for pid in people_ids]) + "'"
    model.AddTag(query, tag_name, int(owner_id), clear)
    try:
        import urllib
        tag_q = urllib.quote(tag_name.encode('utf-8'))
    except:
        tag_q = tag_name.replace(' ', '%20')
    return {
        'ok': True,
        'tag_name': tag_name,
        'count': len(people_ids),
        'cleared': clear,
        'tag_url': '/Tags?tag=' + tag_q,
    }


def _save_config_from_form(cfg):
    if not _is_admin():
        return False, 'Admin only.'
    keys = [
        'ms_orgid', 'hs_orgid', 'week_start_dow', 'event_program_id',
        'event_division_ids', 'leaders_orgid', 'student_leaders_orgid',
        'coaches_orgid', 'onboarding_url', 'involvement_dash_url',
        'kw_decision', 'kw_decision_scope', 'kw_stories', 'baptism_scope',
        'kids_program_id', 'awana_program_id', 'senior_year_orgid',
        'volunteer_program_id', 'volunteer_extra_orgids', 'view_only_role',
        'small_group_names', 'header_logo_url',
    ]
    int_keys = {
        'ms_orgid', 'hs_orgid', 'week_start_dow', 'event_program_id',
        'leaders_orgid', 'student_leaders_orgid', 'coaches_orgid',
        'kids_program_id', 'awana_program_id', 'senior_year_orgid',
        'volunteer_program_id',
    }
    for k in keys:
        val = _form_val(k, _s(cfg.get(k)))
        if k in int_keys:
            cfg[k] = _i(val, 0)
        else:
            cfg[k] = val
    try:
        _save_config(cfg)
        return True, 'Config saved to ' + CONFIG_CONTENT_NAME + '.'
    except Exception, ex:
        return False, 'Save failed: ' + _ex_msg(ex)


def _ensure_group_name(cfg, name):
    name = _s(name)
    if not name:
        return False, 'Group name is required.'
    names = _group_name_list(cfg)
    low = name.lower()
    for n in names:
        if n.lower() == low:
            return True, name
    names.append(name)
    cfg['small_group_names'] = ', '.join(names)
    if _is_admin() or _can_write(cfg):
        try:
            _save_config(cfg)
        except:
            pass
    return True, name


def _student_org_for_person(cfg, people_id):
    people_id = _i(people_id)
    for oid in _standing_orgs(cfg):
        try:
            if model.InOrg(people_id, oid):
                return oid
        except:
            pass
    return 0


def _assign_subgroup(cfg, people_id, group_name, replace_from=''):
    if not _can_write(cfg):
        return False, 'View only — cannot assign.'
    people_id = _i(people_id)
    group_name = _s(group_name)
    if not people_id or not group_name:
        return False, 'Person and group are required.'
    ok, group_name = _ensure_group_name(cfg, group_name)
    if not ok:
        return False, group_name
    targets = []
    soid = _student_org_for_person(cfg, people_id)
    if soid:
        targets.append(soid)
    for oid in _leader_orgs(cfg):
        try:
            if model.InOrg(people_id, oid):
                targets.append(oid)
        except:
            pass
    if not targets:
        return False, 'Person is not on a configured Student or Leader involvement.'
    replace_from = _s(replace_from)
    known = _all_group_names(cfg)
    for oid in targets:
        if replace_from == '*':
            for g in known:
                try:
                    model.RemoveSubGroup(people_id, oid, g)
                except:
                    pass
        elif replace_from:
            try:
                model.RemoveSubGroup(people_id, oid, replace_from)
            except:
                pass
        try:
            model.AddSubGroup(people_id, oid, group_name)
        except Exception, ex:
            return False, _ex_msg(ex)
    return True, 'Assigned to ' + group_name + '.'


def _assign_many(cfg, ids_csv, group_name, replace_from='', add_only=False):
    ids = _parse_people_ids(ids_csv)
    if not ids:
        return False, 'Select at least one person.'
    ok_n = 0
    last = ''
    for pid in ids:
        rf = '' if add_only else replace_from
        ok, msg = _assign_subgroup(cfg, pid, group_name, rf)
        last = msg
        if ok:
            ok_n += 1
    if ok_n:
        return True, str(ok_n) + ' assigned to ' + _s(group_name) + '.'
    return False, last or 'No assignments.'


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _person_link(person):
    pid = _i(person.get('people_id'))
    name = _html(person.get('name') or '(Unknown)')
    if pid <= 0:
        return name
    return '<a href="/Person2/' + str(pid) + '" target="_blank" rel="noopener">' + name + '</a>'


def _people_ids_csv(people):
    ids = []
    seen = {}
    for p in people or []:
        pid = _i(p.get('people_id'))
        if pid and pid not in seen:
            seen[pid] = True
            ids.append(str(pid))
    return ','.join(ids)


def _tag_add_button(people, suggest, can_write):
    if not can_write:
        return ''
    csv = _people_ids_csv(people)
    if not csv:
        return ''
    return (
        '<button type="button" class="btn-tag-add" data-people-ids="'
        + _html(csv) + '" data-tag-suggest="' + _html(suggest)
        + '"><i class="fa fa-tag"></i> Add to Tag</button>'
    )


def _delta_html(n, kind='int'):
    if kind == 'float':
        val = float(n)
        label = ('+' if val > 0 else '') + ('%.1f' % val)
        nshow = val
    else:
        nshow = _i(n)
        label = ('+' if nshow > 0 else '') + str(nshow)
    cls = 'delta-flat'
    if nshow > 0:
        cls = 'delta-up'
    elif nshow < 0:
        cls = 'delta-down'
    return '<span class="delta ' + cls + '">' + _html(label) + '</span>'


def _filter_people(people, grade='', gender='', q=''):
    grade = _s(grade).lower()
    gender = _s(gender).lower()
    q = _s(q).lower()
    out = []
    for p in people or []:
        if grade and _s(p.get('grade')).lower() != grade:
            continue
        if gender and _s(p.get('gender')).lower() != gender:
            continue
        if q:
            blob = (_s(p.get('name')) + ' ' + _s(p.get('school')) + ' ' + _s(p.get('groups'))).lower()
            if q not in blob:
                continue
        out.append(p)
    return out


def _unique_values(people, key):
    seen = {}
    out = []
    for p in people or []:
        v = _s(p.get(key))
        if v and v not in seen:
            seen[v] = True
            out.append(v)
    out.sort(key=lambda x: x.lower())
    return out


def _roster_table(people, extra_label='', can_write=False, tag_suggest='Student Ministry', show_groups=False, show_extra=False, checkboxes=False):
    n = 0
    try:
        n = len(people)
    except:
        n = 0
    html = '<div class="list-actions">'
    html += '<p class="meta-line" style="margin:0"><strong>' + str(n) + '</strong> people · click a header to sort</p>'
    html += _tag_add_button(people, tag_suggest, can_write)
    html += '</div>'
    html += '<div class="table-scroll"><table class="people-table sm-sortable"><thead><tr>'
    if checkboxes:
        html += '<th class="sm-check"><input type="checkbox" class="sm-check-all" title="Select all" /></th>'
    html += '<th class="sm-sort" data-sort="text">Name</th>'
    html += '<th class="sm-sort" data-sort="text">Grade</th>'
    html += '<th class="sm-sort" data-sort="text">Gender</th>'
    html += '<th class="sm-sort" data-sort="num">Age</th>'
    html += '<th class="sm-sort" data-sort="text">School</th>'
    if show_groups:
        html += '<th class="sm-sort" data-sort="text">Groups</th>'
    if show_extra:
        html += '<th class="sm-sort" data-sort="text">' + _html(extra_label or 'Detail') + '</th>'
    html += '</tr></thead><tbody>'
    cols = 5 + (1 if checkboxes else 0) + (1 if show_groups else 0) + (1 if show_extra else 0)
    if not people:
        html += '<tr><td colspan="' + str(cols) + '"><div class="empty-state">No people</div></td></tr>'
    for p in people or []:
        html += '<tr>'
        if checkboxes:
            html += '<td><input type="checkbox" class="sm-row-check" name="pid" value="' + str(_i(p.get('people_id'))) + '" /></td>'
        html += '<td>' + _person_link(p) + '</td>'
        html += '<td>' + _html(p.get('grade')) + '</td>'
        html += '<td>' + _html(p.get('gender')) + '</td>'
        html += '<td>' + _html(p.get('age')) + '</td>'
        html += '<td>' + _html(p.get('school')) + '</td>'
        if show_groups:
            html += '<td>' + _html(p.get('groups')) + '</td>'
        if show_extra:
            html += '<td>' + _html(p.get('extra')) + '</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


def _breakdown_cards(counts, view, key_name):
    html = '<div class="stats-grid compact">'
    items = list(counts.items())
    try:
        items.sort(key=lambda x: (-x[1], _s(x[0]).lower()))
    except:
        pass
    for label, n in items:
        href = _script_path() + '?view=' + view + '&' + key_name + '=' + model.UrlEncode(_s(label))
        html += '<a class="stat-card link-card" href="' + href + '">'
        html += '<div class="stat-value">' + str(_i(n)) + '</div>'
        html += '<div class="stat-label">' + _html(label) + '</div></a>'
    if not items:
        html += '<div class="stat-card"><div class="stat-value">0</div><div class="stat-label">No data</div></div>'
    html += '</div>'
    return html


def _age_bucket(age):
    n = _i(age, -1)
    if n < 0:
        return 'Unknown'
    if n <= 12:
        return '11–12'
    if n <= 14:
        return '13–14'
    if n <= 16:
        return '15–16'
    if n <= 18:
        return '17–18'
    return '19+'


def _header_hero_html(cfg):
    """Refuge Students logo on the Downriver header."""
    url = _s((cfg or {}).get('header_logo_url')) or HEADER_LOGO_URL
    if not url:
        return ''
    html = '<div class="sm-header-hero">'
    html += '<img src="' + _html(url) + '" alt="' + _html(APP_TITLE) + '" />'
    html += '</div>'
    return html


def _nav(view, is_admin):
    html = '<nav class="dash-nav" id="sm-dash-nav" aria-label="' + _html(APP_TITLE) + '">'
    html += '<button type="button" class="dash-nav-caret" id="sm-nav-caret" aria-expanded="true" title="Collapse menu">'
    html += '<i class="fa fa-caret-up" aria-hidden="true"></i></button>'
    html += '<div class="dash-nav-body">'
    for seg_label, tabs in NAV_SEGMENTS:
        links = []
        for key, label in tabs:
            if key == 'config' and not is_admin:
                continue
            cls = 'dash-tab' + (' active' if key == view else '')
            links.append('<a class="' + cls + '" href="' + _script_path() + '?view=' + key + '">' + _html(label) + '</a>')
        if not links:
            continue
        seg_cls = 'seg-home'
        low = _s(seg_label).lower()
        if low == 'people':
            seg_cls = 'seg-people'
        elif low == 'ministry':
            seg_cls = 'seg-ops'
        elif low == 'admin':
            seg_cls = 'seg-admin'
        html += '<div class="dash-nav-segment ' + seg_cls + '">'
        if seg_label:
            html += '<span class="dash-nav-label">' + _html(seg_label) + '</span>'
        html += '<div class="dash-tabs">' + ''.join(links) + '</div></div>'
    html += '</div></nav>'
    return html


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _view_home(cfg, can_write):
    fy_s, fy_e = _fy_bounds()
    att = _attendance_bundle(cfg)
    decisions = _people_with_keywords(
        [_s(cfg.get('kw_decision')), _s(cfg.get('kw_decision_scope'))], True, cfg)
    baptisms = _baptism_people(cfg)
    events = _fy_events(cfg)
    uniq, raw, enroll_people = _event_enrollments(cfg, events)
    html = '<div class="cover-head"><h2>Home</h2>'
    html += '<p class="meta-line">Ministry year ' + _html(_ymd(fy_s)) + ' – ' + _html(_ymd(_add_days(fy_e, -1))) + '</p></div>'

    html += '<div class="stats-grid">'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=decisions">'
    html += '<div class="stat-value">' + str(len(decisions)) + '</div>'
    html += '<div class="stat-label">Decisions (FY)</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=baptisms">'
    html += '<div class="stat-value">' + str(len(baptisms)) + '</div>'
    html += '<div class="stat-label">Baptisms (FY)</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=attendance">'
    html += '<div class="stat-value">' + str(att['this_week']) + '</div>'
    html += '<div class="stat-label">This week present</div>'
    html += '<div class="stat-sub">WoW ' + _delta_html(att['wow']) + ' · LY week ' + _delta_html(att['yoy_week']) + '</div></a>'
    html += '<div class="stat-card">'
    html += '<div class="stat-value">' + ('%.1f' % float(att['month_avg'])) + '</div>'
    html += '<div class="stat-label">Month avg attendance</div>'
    html += '<div class="stat-sub">vs last mo ' + _delta_html(att['month_delta'], 'float')
    html += ' · vs LY ' + _delta_html(att['month_yoy'], 'float') + '</div></div>'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(events)) + '</div>'
    html += '<div class="stat-label">Events since July 1</div></div>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=enroll_unique">'
    html += '<div class="stat-value">' + str(uniq) + '</div>'
    html += '<div class="stat-label">Unique event enrollments</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=enroll_raw">'
    html += '<div class="stat-value">' + str(raw) + '</div>'
    html += '<div class="stat-label">Raw event enrollments</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=leaders">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'leaders_orgid'))) + '</div>'
    html += '<div class="stat-label">Volunteer leaders</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=students">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'student_leaders_orgid'))) + '</div>'
    html += '<div class="stat-label">Student leaders</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=coaches">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'coaches_orgid'))) + '</div>'
    html += '<div class="stat-label">Small Group Coaches</div></a>'
    html += '</div>'

    html += '<p class="meta-line">Week of ' + _html(_ymd(att['week_start'])) + ' – ' + _html(_ymd(att['week_end']))
    html += ' · last week ' + str(att['last_week']) + ' · last year week ' + str(att['last_year_week']) + '</p>'

    dash = _s(cfg.get('involvement_dash_url')) or '/PyScriptForm/InvolvementDashboard'
    html += '<div class="vbs-card"><h3>Ministry-year events</h3>'
    html += '<p class="meta-line">Past events are grey. Upcoming / in-progress are Azure. Name opens the involvement; icon opens Involvement Dashboard.</p>'
    html += '<div class="table-scroll"><table class="people-table sm-sortable"><thead><tr>'
    html += '<th class="sm-sort" data-sort="text">Event</th>'
    html += '<th class="sm-sort" data-sort="text">When</th>'
    html += '<th class="sm-sort" data-sort="text">Division</th>'
    html += '<th class="sm-sort" data-sort="num">Enrolled</th>'
    html += '<th></th></tr></thead><tbody>'
    if not events:
        html += '<tr><td colspan="5"><div class="empty-state">No FY events yet. Set Program Id on Config.</div></td></tr>'
    upcoming = []
    past = []
    for ev in events:
        if _event_is_past(ev):
            past.append(ev)
        else:
            upcoming.append(ev)
    for ev in upcoming + past:
        past_cls = ' event-past' if _event_is_past(ev) else ' event-upcoming'
        when = _ymd(ev.get('start')) or '—'
        if ev.get('last'):
            when = when + ' – ' + _ymd(ev.get('last'))
        html += '<tr class="' + past_cls + '">'
        html += '<td><a href="/Org/' + str(ev['id']) + '" target="_blank" rel="noopener">' + _html(ev['name']) + '</a></td>'
        html += '<td>' + _html(when) + '</td>'
        html += '<td>' + _html(ev.get('division')) + '</td>'
        html += '<td>' + str(_i(ev.get('member_count'))) + '</td>'
        html += '<td><a class="icon-btn" title="Involvement Dashboard" href="' + _html(dash) + '?org_id=' + str(ev['id'])
        html += '" target="_blank" rel="noopener"><i class="fa fa-bar-chart"></i></a></td></tr>'
    html += '</tbody></table></div></div>'

    drill = _s(_form_val('drill'))
    if drill == 'decisions':
        html += '<div class="vbs-card"><h3>Decisions</h3>'
        html += _roster_table(decisions, 'Note date', can_write, 'SM Decisions', False, True)
        html += '</div>'
    elif drill == 'baptisms':
        html += '<div class="vbs-card"><h3>Baptisms</h3>'
        html += _roster_table(baptisms, 'Baptism date', can_write, 'SM Baptisms', False, True)
        html += '</div>'
    elif drill == 'attendance':
        html += '<div class="vbs-card"><h3>This week present</h3>'
        html += _roster_table(att.get('this_week_people') or [], '', can_write, 'SM This Week', False, False)
        html += '</div>'
    elif drill == 'enroll_unique':
        seen = {}
        uniq_people = []
        for p in enroll_people:
            pid = _i(p.get('people_id'))
            if pid not in seen:
                seen[pid] = True
                uniq_people.append(p)
        html += '<div class="vbs-card"><h3>Unique event enrollments</h3>'
        html += _roster_table(uniq_people, 'Event', can_write, 'SM Event Unique', False, True)
        html += '</div>'
    elif drill == 'enroll_raw':
        html += '<div class="vbs-card"><h3>Raw event enrollments</h3>'
        html += _roster_table(enroll_people, 'Event', can_write, 'SM Event Raw', False, True)
        html += '</div>'
    return html


def _view_volunteers(cfg, can_write):
    which = _s(_form_val('list'), 'leaders')
    boxes = [
        ('leaders', 'Volunteer Leaders', _cfg_i(cfg, 'leaders_orgid')),
        ('students', 'Student Leaders', _cfg_i(cfg, 'student_leaders_orgid')),
        ('coaches', 'Small Group Coaches', _cfg_i(cfg, 'coaches_orgid')),
    ]
    html = '<div class="cover-head"><h2>Volunteers</h2>'
    html += '<p class="meta-line">Current members of the dedicated leader involvements. Onboarding stays in its own tool.</p></div>'
    html += '<div class="cover-cta">'
    html += '<a class="btn-primary" href="' + _html(_s(cfg.get('onboarding_url'))) + '" target="_blank" rel="noopener">Open Volunteer Onboarding</a>'
    html += '</div>'
    html += '<div class="subtabs">'
    for key, label, oid in boxes:
        cls = 'dash-tab' + (' active' if which == key else '')
        html += '<a class="' + cls + '" href="' + _script_path() + '?view=volunteers&list=' + key + '">' + _html(label) + '</a>'
    html += '</div>'
    current = boxes[0]
    for row in boxes:
        if row[0] == which:
            current = row
    people = _org_members([current[2]]) if current[2] else []
    html += '<div class="vbs-card"><h3>' + _html(current[1])
    if current[2]:
        html += ' <a href="/Org/' + str(current[2]) + '" target="_blank" rel="noopener">#' + str(current[2]) + '</a>'
    html += '</h3>'
    if not current[2]:
        html += '<div class="empty-state">Set this Involvement # on the Config tab.</div>'
    else:
        html += _roster_table(people, '', can_write, 'SM ' + current[1], True, False)
    html += '</div>'
    return html


def _view_demographics(cfg, can_write):
    people = _org_members(_standing_orgs(cfg))
    grade_f = _s(_form_val('grade'))
    gender_f = _s(_form_val('gender'))
    school_f = _s(_form_val('school'))
    q = _s(_form_val('q'))
    ages = {}
    grades = {}
    schools = {}
    for p in people:
        ages[_age_bucket(p.get('age'))] = ages.get(_age_bucket(p.get('age')), 0) + 1
        g = _s(p.get('grade')) or 'Unknown'
        grades[g] = grades.get(g, 0) + 1
        sch = _s(p.get('school')) or 'Unknown'
        schools[sch] = schools.get(sch, 0) + 1
    filtered = _filter_people(people, grade_f, gender_f, q)
    if school_f:
        tmp = []
        for p in filtered:
            sch = _s(p.get('school')) or 'Unknown'
            if sch.lower() == school_f.lower():
                tmp.append(p)
        filtered = tmp
    html = '<div class="cover-head"><h2>Demographics</h2>'
    html += '<p class="meta-line">Standing Middle School + High School members. School uses People.SchoolOther (audit if empty).</p></div>'
    html += '<h3>Age</h3>' + _breakdown_cards(ages, 'demographics', 'q')
    html += '<h3>Grade</h3>' + _breakdown_cards(grades, 'demographics', 'grade')
    html += '<h3>School</h3>' + _breakdown_cards(schools, 'demographics', 'school')
    bdays = _birthday_people(_standing_orgs(cfg))
    html += '<div class="vbs-card"><h3>Birthdays this month</h3>'
    html += _roster_table(bdays, 'Birthday', can_write, 'SM Birthdays', False, True)
    html += '</div>'
    html += '<div class="vbs-card"><h3>Master roster</h3>'
    html += '<form class="filter-bar" method="get" action="' + _script_path() + '">'
    html += '<input type="hidden" name="view" value="demographics" />'
    html += '<input type="search" name="q" value="' + _html(q) + '" placeholder="Search name" />'
    html += '<select name="grade"><option value="">All grades</option>'
    for g in _unique_values(people, 'grade'):
        sel = ' selected' if g == grade_f else ''
        html += '<option value="' + _html(g) + '"' + sel + '>' + _html(g) + '</option>'
    html += '</select><select name="gender"><option value="">All genders</option>'
    for g in ('Male', 'Female', 'Unknown'):
        sel = ' selected' if g.lower() == gender_f.lower() else ''
        html += '<option value="' + _html(g) + '"' + sel + '>' + _html(g) + '</option>'
    html += '</select><button type="submit" class="btn-secondary">Filter</button></form>'
    html += _roster_table(filtered, '', can_write, 'SM Roster', True, False)
    html += '</div>'
    return html


def _attrition_pairs(people):
    """Census ratio current(N+1) / current(N) for grades 6–12. Not a true cohort."""
    counts = {}
    buckets = {}
    for p in people or []:
        n = _grade_key(p.get('grade'))
        if n < 6 or n > 12:
            continue
        counts[n] = counts.get(n, 0) + 1
        if n not in buckets:
            buckets[n] = []
        buckets[n].append(p)
    rows = []
    g = 6
    while g < 12:
        a = counts.get(g, 0)
        b = counts.get(g + 1, 0)
        rate = None
        if a > 0:
            rate = 1.0 - (float(b) / float(a))
        rows.append({
            'from': g,
            'to': g + 1,
            'from_n': a,
            'to_n': b,
            'rate': rate,
            'from_people': buckets.get(g) or [],
            'to_people': buckets.get(g + 1) or [],
        })
        g += 1
    return rows


def _view_ministry(cfg, can_write):
    stories = _people_with_keywords([_s(cfg.get('kw_stories'))], True, cfg)
    baptisms = _baptism_people(cfg)
    decisions = _people_with_keywords(
        [_s(cfg.get('kw_decision')), _s(cfg.get('kw_decision_scope'))], True, cfg)
    standing = _org_members(_standing_orgs(cfg))
    kids_progs = []
    for k in ('kids_program_id', 'awana_program_id'):
        n = _cfg_i(cfg, k)
        if n > 0:
            kids_progs.append(n)
    kids_people = _people_on_programs(kids_progs)
    sixth = []
    for p in standing:
        if _grade_key(p.get('grade')) == 6:
            sixth.append(p)
    denom = len(kids_people)
    handoff_rate = None
    # Snapshot: 6th on Refuge vs current Kids/Awana membership (not a true cohort)
    if denom > 0:
        handoff_rate = 1.0 - (float(len(sixth)) / float(denom))

    senior_oid = _cfg_i(cfg, 'senior_year_orgid')
    serving = _serving_outside(cfg)
    pairs = _attrition_pairs(standing)

    html = '<div class="cover-head"><h2>Ministry</h2>'
    html += '<p class="meta-line">FY notes, baptisms, and grade census. Adjacent-grade rates are current census ratios until a true cohort is locked (Q9).</p></div>'
    html += '<div class="stats-grid">'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(stories)) + '</div><div class="stat-label">Stories of Transformation</div></div>'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(baptisms)) + '</div><div class="stat-label">Baptisms</div></div>'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(decisions)) + '</div><div class="stat-label">Decisions</div></div>'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(sixth)) + ' / ' + str(denom) + '</div>'
    html += '<div class="stat-label">6th on Refuge / Kids+Awana now</div>'
    if handoff_rate is not None:
        html += '<div class="stat-sub">census gap ' + ('%.0f' % (handoff_rate * 100.0)) + '%</div>'
    html += '</div>'
    if senior_oid > 0:
        html += '<div class="stat-card"><div class="stat-value">' + str(_org_member_count(senior_oid)) + '</div>'
        html += '<div class="stat-label">Senior Year of Discipleship</div></div>'
    else:
        html += '<div class="stat-card"><div class="stat-value">—</div><div class="stat-label">Senior Year (placeholder)</div></div>'
    html += '<div class="stat-card"><div class="stat-value">' + str(len(serving)) + '</div>'
    html += '<div class="stat-label">Serving outside Refuge</div></div>'
    html += '</div>'

    html += '<div class="vbs-card"><h3>Grade-to-grade census</h3>'
    html += '<div class="table-scroll"><table class="people-table"><thead><tr>'
    html += '<th>From</th><th>To</th><th>From #</th><th>To #</th><th>Gap</th></tr></thead><tbody>'
    for row in pairs:
        gap = '—'
        if row['rate'] is not None:
            gap = ('%.0f' % (row['rate'] * 100.0)) + '%'
        html += '<tr><td>Grade ' + str(row['from']) + '</td><td>Grade ' + str(row['to']) + '</td>'
        html += '<td>' + str(row['from_n']) + '</td><td>' + str(row['to_n']) + '</td><td>' + gap + '</td></tr>'
    html += '</tbody></table></div></div>'

    html += '<div class="vbs-card"><h3>Stories of Transformation</h3>'
    html += _roster_table(stories, 'Note date', can_write, 'SM Stories', False, True) + '</div>'
    html += '<div class="vbs-card"><h3>Baptisms</h3>'
    html += _roster_table(baptisms, 'Baptism date', can_write, 'SM Baptisms', False, True) + '</div>'
    html += '<div class="vbs-card"><h3>Decisions</h3>'
    html += _roster_table(decisions, 'Note date', can_write, 'SM Decisions', False, True) + '</div>'
    html += '<div class="vbs-card"><h3>Current 6th grade (Refuge)</h3>'
    html += _roster_table(sixth, '', can_write, 'SM 6th', True, False) + '</div>'
    html += '<div class="vbs-card"><h3>Students serving outside Refuge</h3>'
    html += '<p class="meta-line">Refuge + Volunteer Program (or extra Org#s). Audit the allow-list on Config.</p>'
    html += _roster_table(serving, '', can_write, 'SM Serving', True, False) + '</div>'
    return html


def _person_in_group(person, group_name):
    g = ',' + _s(person.get('groups')).replace(', ', ',').lower() + ','
    return (',' + _s(group_name).lower() + ',') in g


def _view_groups(cfg, can_write):
    names = _all_group_names(cfg)
    students = _org_members(_standing_orgs(cfg))
    leaders = _org_members(_leader_orgs(cfg))
    grade_f = _s(_form_val('grade'))
    gender_f = _s(_form_val('gender'))
    q = _s(_form_val('q'))
    filtered = _filter_people(students, grade_f, gender_f, q)

    html = '<div class="cover-head"><h2>Small Groups</h2>'
    html += '<p class="meta-line">Same SubGroup name on student and leader involvements. Assign can add a second group; Move replaces one name.</p></div>'

    html += '<div class="group-grid">'
    if not names:
        html += '<div class="empty-state">No groups yet. Create one below.</div>'
    for gname in names:
        g_leaders = []
        g_kids = []
        for p in leaders:
            if _person_in_group(p, gname):
                g_leaders.append(p)
        for p in students:
            if _person_in_group(p, gname):
                g_kids.append(p)
        html += '<div class="group-card">'
        html += '<h3>' + _html(gname) + '</h3>'
        html += '<p class="meta-line">' + str(len(g_leaders)) + ' leaders · ' + str(len(g_kids)) + ' students</p>'
        html += '<div class="group-leaders">'
        if g_leaders:
            bits = []
            for p in g_leaders:
                bits.append(_person_link(p))
            html += '<p>' + ', '.join(bits) + '</p>'
        else:
            html += '<p class="meta-line">No leaders assigned</p>'
        html += '</div>'
        html += _tag_add_button(g_leaders + g_kids, 'SM ' + gname, can_write)
        html += '</div>'
    html += '</div>'

    html += '<div class="vbs-card"><h3>Assign</h3>'
    if not can_write:
        html += '<p class="meta-line">View only — assignments are disabled.</p>'
    html += '<form method="get" action="' + _script_path() + '" class="filter-bar">'
    html += '<input type="hidden" name="view" value="groups" />'
    html += '<input type="search" name="q" value="' + _html(q) + '" placeholder="Search name" />'
    html += '<select name="grade"><option value="">All grades</option>'
    for g in _unique_values(students, 'grade'):
        sel = ' selected' if g == grade_f else ''
        html += '<option value="' + _html(g) + '"' + sel + '>' + _html(g) + '</option>'
    html += '</select><select name="gender"><option value="">All genders</option>'
    for g in ('Male', 'Female', 'Unknown'):
        sel = ' selected' if g.lower() == gender_f.lower() else ''
        html += '<option value="' + _html(g) + '"' + sel + '>' + _html(g) + '</option>'
    html += '</select>'
    html += '<button type="submit" class="btn-secondary">Filter list</button></form>'
    html += '<form method="post" action="' + _script_path() + '" class="assign-form">'
    html += '<input type="hidden" name="view" value="groups" />'
    html += '<div class="filter-bar">'
    html += '<select name="group_name"><option value="">Choose group</option>'
    for gname in names:
        html += '<option value="' + _html(gname) + '">' + _html(gname) + '</option>'
    html += '</select>'
    html += '<input type="text" name="new_group" placeholder="New group name" />'
    if can_write:
        html += '<button type="submit" name="action" value="sg_create" class="btn-secondary">Create group</button>'
        html += '<button type="submit" name="action" value="sg_add" class="btn-primary">Add to group</button>'
        html += '<button type="submit" name="action" value="sg_move" class="btn-secondary">Move to group</button>'
        html += '<label class="option-row"><input type="checkbox" name="add_only" value="1" checked /> Keep existing groups (add)</label>'
    html += '</div>'
    html += '<p class="meta-line">Select people below. Add keeps other groups. Move clears known group tags on that person, then assigns the new one.</p>'
    html += '<h4>Students</h4>'
    html += _roster_table(filtered, '', can_write, 'SM Assign', True, False, True)
    html += '<h4>Leaders (from dedicated involvements)</h4>'
    html += _roster_table(leaders, '', can_write, 'SM Leaders', True, False, True)
    html += '</form></div>'
    return html


def _cfg_field(cfg, key, label, hint=''):
    html = '<label class="cfg-field">' + _html(label)
    html += '<input type="text" name="' + _html(key) + '" value="' + _html(cfg.get(key)) + '" />'
    if hint:
        html += '<span class="meta-line">' + _html(hint) + '</span>'
    html += '</label>'
    return html


def _view_config(cfg):
    html = '<div class="cover-head"><h2>Config</h2>'
    html += '<p class="meta-line">Stored as Special Content Text <code>' + _html(CONFIG_CONTENT_NAME) + '</code>. '
    html += _html(_CONFIG_LOAD_INFO) + '</p></div>'
    html += '<form method="post" action="' + _script_path() + '" class="cfg-form">'
    html += '<input type="hidden" name="view" value="config" />'
    html += '<input type="hidden" name="action" value="save_config" />'
    html += '<div class="vbs-card"><h3>Standing weekly orgs</h3>'
    html += _cfg_field(cfg, 'ms_orgid', 'Middle School Org#')
    html += _cfg_field(cfg, 'hs_orgid', 'High School Org#')
    html += _cfg_field(cfg, 'week_start_dow', 'Week start (0=Mon … 6=Sun)', 'Default 2 = Wednesday')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Events (Prog/Div)</h3>'
    html += _cfg_field(cfg, 'event_program_id', 'Student Ministry Program Id')
    html += _cfg_field(cfg, 'event_division_ids', 'Division Ids (comma-separated, optional)')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Leader involvements</h3>'
    html += _cfg_field(cfg, 'leaders_orgid', 'Volunteer Leaders Org#')
    html += _cfg_field(cfg, 'student_leaders_orgid', 'Student Leaders Org#')
    html += _cfg_field(cfg, 'coaches_orgid', 'Small Group Coaches Org#')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Keywords &amp; URLs</h3>'
    html += _cfg_field(cfg, 'kw_decision', 'Decision keyword')
    html += _cfg_field(cfg, 'kw_decision_scope', 'Decision scope keyword (AND)')
    html += _cfg_field(cfg, 'kw_stories', 'Stories of Transformation keyword')
    html += _cfg_field(cfg, 'onboarding_url', 'Volunteer Onboarding URL')
    html += _cfg_field(cfg, 'involvement_dash_url', 'Involvement Dashboard URL')
    html += _cfg_field(cfg, 'baptism_scope', 'Baptism scope', 'standing = MS/HS members only')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Ministry comparisons</h3>'
    html += _cfg_field(cfg, 'kids_program_id', 'Faith Kids Program Id')
    html += _cfg_field(cfg, 'awana_program_id', 'Awana Program Id')
    html += _cfg_field(cfg, 'senior_year_orgid', 'Senior Year Org# (0 = placeholder)')
    html += _cfg_field(cfg, 'volunteer_program_id', 'Volunteer Program Id (serving outside)')
    html += _cfg_field(cfg, 'volunteer_extra_orgids', 'Extra volunteer Org#s (comma-separated)')
    html += _cfg_field(cfg, 'view_only_role', 'View Only role name')
    html += _cfg_field(cfg, 'small_group_names', 'Known small group names (comma-separated)')
    html += _cfg_field(cfg, 'header_logo_url', 'Header logo URL', 'Shown on the Downriver header')
    html += '</div>'
    html += '<button type="submit" class="btn-primary">Save config</button>'
    html += '</form>'
    return html


def _view_denied():
    return (
        '<div class="info-banner danger"><strong>No access.</strong> '
        'Need (Staff or Elders) and Next Gen, or Admin.</div>'
    )


def _view_body(view, cfg, can_write):
    if view == 'home':
        return _view_home(cfg, can_write)
    if view == 'volunteers':
        return _view_volunteers(cfg, can_write)
    if view == 'demographics':
        return _view_demographics(cfg, can_write)
    if view == 'ministry':
        return _view_ministry(cfg, can_write)
    if view == 'groups':
        return _view_groups(cfg, can_write)
    if view == 'config':
        return _view_config(cfg)
    return '<div class="empty-state">Unknown view</div>'


def _css():
    bp = BRAND['black-pearl']
    dr = BRAND['downriver']
    az = BRAND['azure']
    hk = BRAND['hawkes']
    ln = BRAND['linen']
    fo = BRAND['forest']
    vm = BRAND['vermillion']
    return (
        '.sm-root{display:block!important;visibility:visible!important;max-width:1400px;margin:0 auto;'
        'padding:20px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;'
        'background:#f5f5f5!important;color:#1e293b!important;min-height:240px}'
        '.dashboard-header{background:' + dr + ';color:#fff!important;padding:18px 24px 16px;border-radius:12px;'
        'margin:0 auto 12px auto;box-shadow:0 4px 15px rgba(1,43,88,.35);text-align:center;max-width:960px}'
        '.sm-header-hero{text-align:center;margin:0 0 8px 0;line-height:0}'
        '.sm-header-hero img{display:block;margin:0 auto;max-height:110px;max-width:min(92%,720px);'
        'width:auto;height:auto;object-fit:contain}'
        '.dashboard-header h1{margin:0 0 4px;font-size:18px;font-weight:600;color:#fff!important}'
        '.role-pill{display:inline-block;margin-top:8px;padding:3px 10px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.35)}'
        '.dash-nav{text-align:center;margin:0 0 14px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:8px 28px 8px 10px;box-shadow:0 1px 4px rgba(0,0,0,.04);position:relative}'
        '.dash-nav-caret{position:absolute;top:4px;right:6px;width:22px;height:22px;border:none;background:transparent;'
        'color:#64748b;cursor:pointer}'
        '.dash-nav.is-collapsed .dash-nav-body{display:none!important}'
        '.dash-nav-segment{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:4px 6px;margin:0 0 4px}'
        '.dash-nav-label{font-size:10px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:#64748b;margin-right:4px}'
        '.dash-tab{display:inline-block;border:1px solid #e2e8f0;background:#fff;color:#475569!important;padding:4px 10px;'
        'border-radius:6px;font-weight:600;font-size:12px;text-decoration:none!important;margin:1px 2px}'
        '.dash-tab:hover{border-color:' + az + ';color:' + dr + '!important}'
        '.dash-tab.active{border-color:' + dr + ';background:' + dr + ';color:#fff!important}'
        '.dash-nav-segment.seg-people .dash-tab.active{border-color:' + az + ';background:' + az + '}'
        '.dash-nav-segment.seg-ops .dash-tab.active{border-color:' + fo + ';background:' + fo + '}'
        '.dash-nav-segment.seg-admin .dash-tab.active{border-color:' + bp + ';background:' + bp + '}'
        '.subtabs{margin:0 0 12px}'
        '.cover-head h2{margin:0 0 4px;color:' + bp + '}'
        '.meta-line{color:#64748b;font-size:13px;margin:4px 0 10px}'
        '.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin:0 0 16px}'
        '.stats-grid.compact{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}'
        '.stat-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,.04);'
        'text-decoration:none!important;color:inherit!important;display:block}'
        '.stat-card.link-card:hover{border-color:' + az + '}'
        '.stat-value{font-size:28px;font-weight:700;color:' + dr + ';line-height:1.1}'
        '.stat-label{font-size:12px;font-weight:600;color:#475569;margin-top:4px}'
        '.stat-sub{font-size:11px;color:#64748b;margin-top:4px}'
        '.delta-up{color:' + fo + ';font-weight:700}'
        '.delta-down{color:' + vm + ';font-weight:700}'
        '.delta-flat{color:#64748b;font-weight:600}'
        '.vbs-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:0 0 16px;'
        'box-shadow:0 1px 4px rgba(0,0,0,.04)}'
        '.vbs-card h3{margin:0 0 8px;color:' + bp + ';font-size:18px}'
        '.people-table{width:100%;border-collapse:collapse;font-size:13px}'
        '.people-table th,.people-table td{padding:7px 8px;border-bottom:1px solid #e2e8f0;text-align:left}'
        '.people-table th{background:' + ln + ';color:' + bp + ';font-size:12px}'
        '.sm-sort{cursor:pointer}'
        '.people-table a{color:' + az + ';font-weight:600;text-decoration:none}'
        '.people-table a:hover{text-decoration:underline}'
        '.table-scroll{overflow-x:auto}'
        '.empty-state{padding:16px;color:#64748b;text-align:center}'
        '.list-actions{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 8px;flex-wrap:wrap}'
        '.btn-primary,.btn-secondary,.btn-tag-add,.btn-tag-confirm{border:none;border-radius:8px;padding:8px 14px;'
        'font-weight:700;cursor:pointer;font-size:13px;text-decoration:none!important;display:inline-block}'
        '.btn-primary,.btn-tag-confirm{background:' + dr + ';color:#fff!important}'
        '.btn-secondary{background:#fff;color:' + dr + '!important;border:1px solid #cbd5e1}'
        '.btn-tag-add{background:' + hk + ';color:' + dr + '!important}'
        '.icon-btn{color:' + az + ';font-size:16px;padding:4px}'
        'tr.event-upcoming td:first-child a{color:' + az + '}'
        'tr.event-past{color:#94a3b8}'
        'tr.event-past a{color:#94a3b8!important}'
        '.info-banner{background:' + hk + ';border:1px solid ' + az + ';color:' + bp + ';padding:10px 12px;border-radius:8px;margin:0 0 12px}'
        '.info-banner.danger{background:#fef2f2;border-color:' + vm + ';color:#7f1d1d}'
        '.filter-bar,.assign-form .filter-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}'
        '.filter-bar input,.filter-bar select,.cfg-field input{padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:13px}'
        '.cfg-form .vbs-card{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}'
        '.cfg-form h3{grid-column:1/-1}'
        '.cfg-field{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:600;color:' + bp + '}'
        '.group-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin:0 0 16px}'
        '.group-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px}'
        '.group-card h3{margin:0 0 4px;color:' + dr + '}'
        '.cover-cta{margin:0 0 14px}'
        '.tag-modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,20,41,.45);z-index:40;align-items:center;justify-content:center}'
        '.tag-modal-overlay.visible{display:flex}'
        '.tag-modal{background:#fff;border-radius:12px;max-width:420px;width:90%;padding:0;box-shadow:0 8px 30px rgba(0,0,0,.2)}'
        '.tag-modal-header{background:' + dr + ';color:#fff;padding:12px 16px;border-radius:12px 12px 0 0;font-weight:700}'
        '.tag-modal-body{padding:14px 16px}'
        '.tag-modal-body input[type=text]{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}'
        '.tag-modal-footer{padding:10px 16px 14px;display:flex;justify-content:flex-end;gap:8px}'
        '.option-row{display:flex;gap:8px;align-items:flex-start;font-size:12px;margin:8px 0;font-weight:500}'
    )


def _page_script():
    path = _script_path()
    return (
        "var scriptUrl='" + path.replace("'", "\\'") + "';"
        "function $(s,r){return (r||document).querySelector(s);}"
        "function addClass(el,c){if(el) el.className=(el.className+' '+c).replace(/^\\s+|\\s+$/g,'');}"
        "function removeClass(el,c){if(!el)return;el.className=(' '+el.className+' ').replace(' '+c+' ',' ').replace(/^\\s+|\\s+$/g,'');}"
        "var pending=[];"
        "function parseIds(csv){var o=[],s={};String(csv||'').split(',').forEach(function(x){var n=parseInt(x,10);if(n>0&&!s[n]){s[n]=1;o.push(n);}});return o;}"
        "function openTag(ids,sug){pending=ids||[];if(!pending.length){alert('No people in this list.');return;}"
        "var c=$('#tag-modal-count');if(c)c.textContent=pending.length+' people will be added.';"
        "var i=$('#tag-name-input');if(i)i.value=sug||'';var o=$('#tag-modal-overlay');if(o)addClass(o,'visible');}"
        "function closeTag(){var o=$('#tag-modal-overlay');if(o)removeClass(o,'visible');pending=[];}"
        "function submitTag(){var i=$('#tag-name-input');var name=i?String(i.value||'').replace(/^\\s+|\\s+$/g,''):'';"
        "if(!name){alert('Enter a tag name.');return;}if(!pending.length){alert('No people.');return;}"
        "var mode=$('input[name=tag-mode]:checked');var clear=mode&&mode.value==='clear';"
        "var openEl=$('#tag-open-when-done');var openDone=openEl?!!openEl.checked:true;"
        "var ids=pending.join(',');closeTag();"
        "var body='ajax=true&action=add_to_tag&people_ids='+encodeURIComponent(ids)+'&tag_name='+encodeURIComponent(name)+'&clear_first='+(clear?'1':'0');"
        "var x=new XMLHttpRequest();x.open('POST',scriptUrl,true);x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');"
        "x.onreadystatechange=function(){if(x.readyState!==4)return;var d=null;try{d=JSON.parse(x.responseText);}catch(e){alert('Tag failed.');return;}"
        "if(d&&d.error){alert(d.error);return;}if(openDone&&d&&d.tag_url)window.open(d.tag_url,'_blank','noopener');else alert((d&&d.count?d.count:0)+' added.');};"
        "x.send(body);}"
        "document.addEventListener('click',function(e){var t=e.target;"
        "while(t&&t!==document){if(t.className&&(' '+t.className+' ').indexOf(' btn-tag-add ')>=0){e.preventDefault();openTag(parseIds(t.getAttribute('data-people-ids')),t.getAttribute('data-tag-suggest')||'');return;}"
        "if(t.id==='btn-tag-cancel'){e.preventDefault();closeTag();return;}"
        "if(t.id==='btn-tag-confirm'){e.preventDefault();submitTag();return;}"
        "if(t.id==='sm-nav-caret'){e.preventDefault();var n=document.getElementById('sm-dash-nav');if(n){if((' '+n.className+' ').indexOf(' is-collapsed ')>=0)removeClass(n,'is-collapsed');else addClass(n,'is-collapsed');}return;}"
        "if(t.className&&(' '+t.className+' ').indexOf(' sm-sort ')>=0){e.preventDefault();sortTable(t);return;}"
        "t=t.parentNode;}});"
        "document.addEventListener('change',function(e){if(e.target&&e.target.className&&e.target.className.indexOf('sm-check-all')>=0){"
        "var on=!!e.target.checked;var tbl=e.target.closest?e.target.closest('table'):null;if(!tbl)return;"
        "var boxes=tbl.querySelectorAll('.sm-row-check');for(var i=0;i<boxes.length;i++)boxes[i].checked=on;}});"
        "function sortTable(th){var table=th.parentNode;while(table&&table.tagName!=='TABLE')table=table.parentNode;"
        "if(!table)return;var idx=th.cellIndex;var kind=th.getAttribute('data-sort')||'text';"
        "var rows=Array.prototype.slice.call(table.tBodies[0].rows);"
        "var dir=th.getAttribute('data-dir')==='asc'?'desc':'asc';"
        "var heads=table.tHead?table.tHead.rows[0].cells:[];for(var i=0;i<heads.length;i++)heads[i].removeAttribute('data-dir');"
        "th.setAttribute('data-dir',dir);"
        "rows.sort(function(a,b){var ta=(a.cells[idx]?a.cells[idx].textContent:'').replace(/^\\s+|\\s+$/g,'');"
        "var tb=(b.cells[idx]?b.cells[idx].textContent:'').replace(/^\\s+|\\s+$/g,'');"
        "if(kind==='num'){var na=parseFloat(ta)||0,nb=parseFloat(tb)||0;return dir==='asc'?na-nb:nb-na;}"
        "ta=ta.toLowerCase();tb=tb.toLowerCase();if(ta<tb)return dir==='asc'?-1:1;if(ta>tb)return dir==='asc'?1:-1;return 0;});"
        "var tbod=table.tBodies[0];for(var j=0;j<rows.length;j++)tbod.appendChild(rows[j]);}"
    )


def _page(view, cfg, msg, can_write, can_admin, can_access):
    try:
        if not can_access:
            body = _view_denied()
        else:
            body = _view_body(view, cfg, can_write)
    except Exception, ex:
        body = (
            '<div class="info-banner danger"><strong>View error (' + _html(view) + ')</strong>'
            '<pre style="white-space:pre-wrap">' + _html(_ex_msg(ex)) + '\n' + _html(traceback.format_exc()) + '</pre></div>'
        )
    alert = ''
    if msg:
        alert = '<div class="info-banner">' + _html(msg) + '</div>'
    if _LOAD_WARNINGS:
        alert += '<div class="info-banner danger"><strong>Data load warning</strong><ul>'
        for w in _LOAD_WARNINGS:
            alert += '<li>' + _html(w) + '</li>'
        alert += '</ul></div>'
    if can_admin:
        role_label = 'Admin'
    elif can_write:
        role_label = 'Ministry leader'
    elif can_access:
        role_label = 'View only'
    else:
        role_label = 'No access'
    html = '<style type="text/css">' + _css() + '</style>'
    html += '<div class="sm-root sm-view-' + _html(view) + '">'
    html += '<div class="tag-modal-overlay" id="tag-modal-overlay" role="dialog">'
    html += '<div class="tag-modal"><div class="tag-modal-header" id="tag-modal-title">Add to Tag</div>'
    html += '<div class="tag-modal-body"><p class="tag-modal-meta" id="tag-modal-count"></p>'
    html += '<label for="tag-name-input">Tag name</label>'
    html += '<input type="text" id="tag-name-input" maxlength="50" autocomplete="off" />'
    html += '<div class="tag-modal-options">'
    html += '<label class="option-row"><input type="radio" name="tag-mode" value="append" checked />'
    html += '<span>Append — keep anyone already on the tag</span></label>'
    html += '<label class="option-row"><input type="radio" name="tag-mode" value="clear" />'
    html += '<span>Clear first — empty the tag, then add only this list</span></label>'
    html += '<label class="option-row"><input type="checkbox" id="tag-open-when-done" checked />'
    html += '<span>Open the tag in a new tab when done</span></label>'
    html += '</div></div><div class="tag-modal-footer">'
    html += '<button type="button" class="btn-secondary" id="btn-tag-cancel">Cancel</button>'
    html += '<button type="button" class="btn-tag-confirm" id="btn-tag-confirm">Add to Tag</button>'
    html += '</div></div></div>'
    html += '<div class="dashboard-header">'
    html += _header_hero_html(cfg)
    html += '<h1>' + _html(APP_TITLE) + '</h1>'
    html += '<div class="role-pill">' + role_label + '</div></div>'
    html += _nav(view, can_admin)
    html += alert
    html += '<div class="sm-main">' + body + '</div></div>'
    try:
        model.Script = _page_script()
    except:
        pass
    return html


def main():
    model.Title = APP_TITLE
    model.Header = APP_TITLE
    model.Styles = ''
    cfg = _load_config()
    can_admin = _is_admin()
    can_access = _can_access(cfg)
    can_write = _can_write(cfg)
    view = _resolve_view(cfg)
    msg = _form_val('msg', '')

    is_ajax = _s(_form_val('ajax')).lower() == 'true'
    if is_ajax:
        action = _form_val('action')
        if action == 'add_to_tag':
            if not can_write:
                _json_out({'error': 'View only.'})
            else:
                try:
                    _json_out(_add_people_to_tag(
                        _form_val('people_ids'),
                        _form_val('tag_name'),
                        _form_val('clear_first'),
                    ))
                except Exception, ex:
                    _json_out({'error': _ex_msg(ex)})
        else:
            _json_out({'error': 'Unknown action'})
        return

    if model.HttpMethod == 'post':
        action = _form_val('action')
        message = 'Unknown action.'
        view = _resolve_view(cfg)
        if action == 'save_config':
            ok, message = _save_config_from_form(cfg)
            view = 'config'
        elif action == 'sg_create':
            name = _s(_form_val('new_group')) or _s(_form_val('group_name'))
            ok, message = _ensure_group_name(cfg, name)
            if ok:
                message = 'Group ready: ' + name
            view = 'groups'
        elif action in ('sg_add', 'sg_move'):
            gname = _s(_form_val('group_name')) or _s(_form_val('new_group'))
            ids = ''
            try:
                from System.Web import HttpContext
                vals = HttpContext.Current.Request.Form.GetValues('pid')
                if vals:
                    ids = ','.join([_s(x) for x in vals])
            except:
                ids = ''
            if not ids:
                ids = _form_val('pid')
            add_only = action == 'sg_add' and _b(_form_val('add_only'))
            replace = ''
            if action == 'sg_move':
                add_only = False
                replace = '*'
            ok, message = _assign_many(cfg, ids, gname, replace, add_only)
            view = 'groups'
        elif action == 'add_to_tag':
            result = _add_people_to_tag(_form_val('people_ids'), _form_val('tag_name'), _form_val('clear_first'))
            if result.get('error'):
                message = result['error']
            else:
                message = str(result.get('count', 0)) + ' people tagged.'
        _redirect(message, view)
        return

    _show(_page(view, cfg, msg, can_write, can_admin, can_access))


try:
    main()
except Exception, ex:
    err = (
        '<div style="background:#fef2f2;border:2px solid #dc2626;color:#991b1b;padding:16px;margin:12px;'
        'border-radius:8px;font-family:sans-serif"><strong>Student Ministry Command Center error</strong>'
        '<pre style="white-space:pre-wrap">' + _html(_ex_msg(ex)) + '\n' + _html(traceback.format_exc()) + '</pre></div>'
    )
    try:
        _show(err)
    except:
        print err
