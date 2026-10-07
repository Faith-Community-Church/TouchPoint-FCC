#Roles=Access
# Script: StudentMinistryCentral.py
# Purpose: Student Ministry Central. Home (attendance, FY
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
import math
import traceback

try:
    import sys
    reload(sys)
    sys.setdefaultencoding('latin-1')
except:
    pass

APP_TITLE = 'Student Ministry Central'
CONFIG_CONTENT_NAME = 'StudentMinistryCentralConfig'
SCRIPT_FALLBACK = 'StudentMinistryCentral'
# All Next Generation involvements (Kids, Awana, Students, events) sit under this Program.
NEXT_GEN_PROGRAM_ID = 1112
# FCC Student Ministry events Division under Program 1112.
EVENT_DIVISION_ID = 46
# Volunteer Program — student serving-outside involvements.
VOLUNTEER_PROGRAM_ID = 1120
# Weekly Sunday in-person service attendance (two meeting times, head count).
SUNDAY_ATTEND_ORGID = 35
HEADER_LOGO_URL = (
    'https://irp.cdn-website.com/395ab2a8/dms3rep/multi/opt/RefugeStudents-logos-40-1920w.png'
)

# Refuge / Student Ministry — Navy + White. Artisan for alerts / accents.
# Dark gray for month headers so they stand apart from navy and Artisan.
BRAND = {
    'navy': '#14283C',
    'white': '#FFFFFF',
    'gray': '#EEF0F2',
    'dark-gray': '#565E66',
    'artisan': '#DD5B58',
}

NAV_TABS_TOP = [
    ('home', 'Home'),
    ('config', 'Config'),
]
NAV_TABS_MAIN = [
    ('volunteers', 'Volunteers'),
    ('demographics', 'Demographics'),
    ('ministry', 'Ministry'),
    ('groups', 'Small Groups'),
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


def _unquote(val):
    """Strip wrapping quotes from Extra Value text. Stored quotes are not needed on screen."""
    s = _s(val)
    while len(s) >= 2 and (
            (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    if s == '' or s == 'None' or s == 'null':
        return ''
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


def _round_half_up(n):
    """0.4 and below down, 0.5 and above up. Returns an int."""
    try:
        x = float(n)
    except:
        return 0
    if x >= 0:
        return int(math.floor(x + 0.5))
    return int(math.ceil(x - 0.5))


def _avg_label(avg, weeks=None):
    if weeks is not None and _i(weeks) <= 0:
        return '—'
    if avg is None:
        return '—'
    return str(_round_half_up(avg))


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


def _url_enc(val):
    try:
        return model.UrlEncode(_s(val))
    except:
        return _s(val).replace(' ', '%20')


def _refresh_href(view):
    """Reload the current view, keeping list/filter/drill query params."""
    href = _script_path() + '?view=' + _s(view or 'home')
    for key in ('drill', 'att', 'list', 'grade', 'gender', 'school', 'q', 'group'):
        val = _s(_form_val(key))
        if val:
            href += '&' + key + '=' + _url_enc(val)
    href += '&refresh=1'
    if _s(_form_val('drill')):
        href += '#sm-drill-list'
    elif view == 'volunteers':
        href += _vol_list_hash(_s(_form_val('list')))
    elif _s(_form_val('section')) == 'serving':
        href += '#sm-serving-beyond'
    elif view == 'demographics' and (
            _s(_form_val('grade')) or _s(_form_val('gender'))
            or _s(_form_val('school')) or _s(_form_val('q'))):
        href += '#sm-filtered-list'
    return href


def _refresh_button(view):
    return (
        '<a class="btn-refresh" href="' + _refresh_href(view) + '" title="Reload this page">'
        '<i class="fa fa-refresh" aria-hidden="true"></i> Refresh</a>'
    )


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


def _date_display(d):
    """User-facing date: July 1, 2026. Accepts date or parseable value."""
    if d is None:
        return ''
    dt = d
    if not isinstance(d, datetime.date):
        dt = _parse_date(d)
    if dt is None:
        return ''
    try:
        return dt.strftime('%B ') + str(int(dt.day)) + ', ' + str(int(dt.year))
    except:
        return _ymd(dt)


def _dt_display(val):
    """Meeting date + time, e.g. Oct 5, 2026 6:30 PM."""
    if _is_null(val):
        return _date_display(val)
    try:
        if hasattr(val, 'Year'):
            y = int(val.Year)
            mo = int(val.Month)
            d = int(val.Day)
            h = int(val.Hour) if hasattr(val, 'Hour') else 0
            mi = int(val.Minute) if hasattr(val, 'Minute') else 0
        else:
            y = int(val.year)
            mo = int(val.month)
            d = int(val.day)
            h = int(getattr(val, 'hour', 0) or 0)
            mi = int(getattr(val, 'minute', 0) or 0)
        hour = h % 12
        if hour == 0:
            hour = 12
        ampm = 'PM' if h >= 12 else 'AM'
        if mi < 10:
            mpart = '0' + str(mi)
        else:
            mpart = str(mi)
        dt = datetime.date(y, mo, d)
        return dt.strftime('%b ') + str(d) + ', ' + str(y) + ' ' + str(hour) + ':' + mpart + ' ' + ampm
    except:
        return _date_display(val)


def _md_display(month, day):
    """Birthday-style date without year: July 1."""
    try:
        dt = datetime.date(2000, _i(month), _i(day))
        return dt.strftime('%B ') + str(int(dt.day))
    except:
        return ''


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


def _parse_date_loose(val):
    """Parse ISO, US, or Month Day, Year strings. Returns None if not a date."""
    dt = _parse_date(val)
    if dt:
        return dt
    s = _s(val).strip()
    if not s:
        return None
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%B %d, %Y', '%b %d, %Y', '%m-%d-%Y', '%Y/%m/%d'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except:
            pass
    return None


def _when_display(ev):
    """When column: meeting dates. One date if same day; otherwise First – Last."""
    first = (ev or {}).get('first')
    last = (ev or {}).get('last')
    first_s = _date_display(first)
    last_s = _date_display(last)
    if first_s and last_s and first_s != last_s:
        return first_s + ' – ' + last_s
    return first_s or last_s or '—'


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


def _academic_year_start(d=None):
    """Academic year starts September 1. Jan–Aug belongs to the prior Sept."""
    if d is None:
        d = _today()
    if d.month >= 9:
        return datetime.date(d.year, 9, 1)
    return datetime.date(d.year - 1, 9, 1)


def _academic_fq_specs(today=None):
    """id, label, subtitle, start, end-exclusive."""
    if today is None:
        today = _today()
    ay_y = _academic_year_start(today).year
    return [
        ('fq1', 'FQ1', 'September', datetime.date(ay_y, 9, 1), datetime.date(ay_y, 10, 1)),
        ('fq2', 'FQ2', 'Oct – Dec', datetime.date(ay_y, 10, 1), datetime.date(ay_y + 1, 1, 1)),
        ('fq3', 'FQ3', 'Jan – Mar', datetime.date(ay_y + 1, 1, 1), datetime.date(ay_y + 1, 4, 1)),
        ('fq4', 'FQ4', 'April – May', datetime.date(ay_y + 1, 4, 1), datetime.date(ay_y + 1, 6, 1)),
    ]


def _merge_meeting_days(*lists):
    by_day = {}
    for days in lists:
        for row in days or []:
            d = row.get('day')
            if not d:
                continue
            by_day[d] = by_day.get(d, 0) + _i(row.get('count'))
    out = []
    keys = list(by_day.keys())
    try:
        keys.sort()
    except:
        pass
    for d in keys:
        n = by_day[d]
        if n > 0:
            out.append({'day': d, 'count': n})
    return out


def _add_years(d, n):
    """Same month/day n years later (or earlier). Feb 29 becomes Feb 28."""
    if d is None:
        return None
    y = d.year + _i(n)
    try:
        return datetime.date(y, d.month, d.day)
    except:
        return datetime.date(y, d.month, 28)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _default_config():
    return {
        'version': 1,
        'ms_orgid': 0,
        'hs_orgid': 0,
        'sunday_attendance_orgid': SUNDAY_ATTEND_ORGID,
        'week_start_dow': 2,
        'awag_division_ids': '',
        'event_program_id': NEXT_GEN_PROGRAM_ID,
        'event_division_ids': str(EVENT_DIVISION_ID),
        'event_date_extra': 'Date',
        'leaders_orgid': 0,
        'student_leaders_orgid': 0,
        'coaches_orgid': 0,
        'onboarding_url': '/PyScriptForm/VolunteerOnboardingDashboard',
        'involvement_dash_url': '/PyScriptForm/InvolvementDashboard',
        'kw_decision': 'Decision to Follow Jesus',
        'kw_decision_scope': 'Refuge Student Ministry',
        'kw_stories': 'Stories of Transformation',
        'baptism_scope': 'standing',
        'next_gen_program_id': NEXT_GEN_PROGRAM_ID,
        'kids_division_id': 0,
        'awana_division_id': 0,
        'senior_year_orgid': 0,
        'volunteer_program_id': VOLUNTEER_PROGRAM_ID,
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
        # Legacy keys: Kids/Awana used to be stored as Program Ids
        if _i(cfg.get('kids_division_id'), 0) <= 0 and _i(parsed.get('kids_program_id'), 0) > 0:
            cfg['kids_division_id'] = _i(parsed.get('kids_program_id'))
        if _i(cfg.get('awana_division_id'), 0) <= 0 and _i(parsed.get('awana_program_id'), 0) > 0:
            cfg['awana_division_id'] = _i(parsed.get('awana_program_id'))
        if _i(cfg.get('next_gen_program_id'), 0) <= 0:
            cfg['next_gen_program_id'] = NEXT_GEN_PROGRAM_ID
        if _i(cfg.get('event_program_id'), 0) <= 0:
            cfg['event_program_id'] = NEXT_GEN_PROGRAM_ID
        if not _s(cfg.get('event_division_ids')).strip():
            cfg['event_division_ids'] = str(EVENT_DIVISION_ID)
        if _i(cfg.get('volunteer_program_id'), 0) <= 0:
            cfg['volunteer_program_id'] = VOLUNTEER_PROGRAM_ID
        if _i(cfg.get('sunday_attendance_orgid'), 0) <= 0:
            cfg['sunday_attendance_orgid'] = SUNDAY_ATTEND_ORGID
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
    """Small group leaders: Volunteer Leaders + SG Coaches. Not Student Lead Team."""
    out = []
    for key in ('leaders_orgid', 'coaches_orgid'):
        n = _cfg_i(cfg, key)
        if n > 0:
            out.append(n)
    return out


def _sg_assign_leader_orgs(cfg):
    return _leader_orgs(cfg)


def _exclude_orgs(cfg):
    seen = {}
    out = []
    extra = _cfg_i(cfg, 'student_leaders_orgid')
    for n in _standing_orgs(cfg) + _leader_orgs(cfg) + [extra]:
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
        'school': _unquote(r.SchoolDistrict) if hasattr(r, 'SchoolDistrict') else '',
        'groups': _s(r.GroupNames) if hasattr(r, 'GroupNames') else '',
        'org_id': _i(r.OrganizationId) if hasattr(r, 'OrganizationId') else 0,
        'org_name': _s(r.OrganizationName) if hasattr(r, 'OrganizationName') else '',
        'extra': _s(r.Extra) if hasattr(r, 'Extra') else '',
    }


def _sql_school_expr():
    """People Extra Value 'School District' (text or code)."""
    return """COALESCE(
        NULLIF(LTRIM(RTRIM(ISNULL(sx.StrValue,''))), ''),
        NULLIF(LTRIM(RTRIM(ISNULL(sx.Data,''))), ''),
        ''
    )"""


def _sql_school_select():
    return _sql_school_expr() + ' AS SchoolDistrict'


def _sql_school_join(people_alias='pe'):
    return """
LEFT JOIN dbo.PeopleExtra sx
ON sx.PeopleId = """ + people_alias + """.PeopleId
AND LOWER(LTRIM(RTRIM(ISNULL(sx.Field,'')))) = 'school district'
"""


def _sql_person_select():
    return """
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName,
    pe.LastName,
    pe.Age,
    """ + _sql_school_select() + """,
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
""" + _sql_school_join('pe')


def _org_members(org_ids, extra_where='', exclude_leaders=False):
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    extra_join = ''
    if exclude_leaders:
        extra_join = ' LEFT JOIN lookup.MemberType lmt ON lmt.Id = om.MemberTypeId '
        extra_where += """
AND ISNULL(lmt.AttendanceTypeId, 0) <> 10
AND UPPER(LTRIM(RTRIM(ISNULL(lmt.Description,'')))) NOT LIKE '%LEADER%'
"""
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
""" + _sql_person_joins() + extra_join + """
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
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.TaskNote tn
""" + joins + """
INNER JOIN dbo.People pe ON pe.PeopleId = tn.AboutPersonId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
WHERE ISNULL(tn.IsArchived, 0) = 0
AND tn.AboutPersonId IS NOT NULL
AND ISNULL(pe.IsDeceased, 0) = 0
""" + fy_sql + """
GROUP BY tn.AboutPersonId, pe.Name2, pe.FirstName, pe.LastName, pe.Age,
        pe.GenderId, gl.Description, sx.StrValue, sx.Data
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
        rec['extra'] = _date_display(r.Extra) if hasattr(r, 'Extra') else ''
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
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel,
    pe.BaptismDate AS Extra
FROM dbo.People pe
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
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
        rec['extra'] = _date_display(r.Extra)
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


def _attend_unique_count(org_ids, start, end):
    """Distinct present people in [start, end)."""
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids or start is None or end is None:
        return 0
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS Cnt
FROM dbo.Attend a
INNER JOIN dbo.People pe ON pe.PeopleId = a.PeopleId
WHERE a.OrganizationId IN (""" + frag + """)
AND a.AttendanceFlag = 1
AND a.MeetingDate >= @d1
AND a.MeetingDate < @d2
AND ISNULL(pe.IsDeceased, 0) = 0
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
        if rows:
            return _i(rows[0].Cnt)
    except Exception, ex:
        _warn('unique attend: ' + _ex_msg(ex))
    return 0


def _sunday_headcount_average(org_id, start, end):
    """FY Sunday average for Inv#35.

    Each Sunday is the SUM of that day's meeting head counts (both service
    times added, never averaged). The mean is then taken across those Sunday
    totals in [start, end).
    """
    org_id = _i(org_id)
    if org_id <= 0 or start is None or end is None:
        return 0.0, 0
    # Do not look past today — FY window is July 1 through now (or FY end).
    today = _today()
    if end > _add_days(today, 1):
        end = _add_days(today, 1)
    sql = """
SELECT m.MeetingDate,
    ISNULL(m.HeadCount, 0) AS HeadCnt,
    ISNULL(m.NumPresent, 0) AS PresentCnt
FROM dbo.Meetings m
WHERE m.OrganizationId = @oid
AND ISNULL(m.DidNotMeet, 0) = 0
AND m.MeetingDate >= @d1
AND m.MeetingDate < @d2
"""
    p = _dd()
    p.AddValue('oid', org_id)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('Sunday head count: ' + _ex_msg(ex))
        return 0.0, 0
    by_day = {}
    for r in rows:
        d = _parse_date(r.MeetingDate)
        if not d or d.weekday() != 6:
            continue
        hc = _i(r.HeadCnt)
        if hc <= 0:
            hc = _i(r.PresentCnt)
        by_day[d] = by_day.get(d, 0) + hc
    vals = []
    for n in by_day.values():
        if n > 0:
            vals.append(n)
    if not vals:
        return 0.0, 0
    avg = float(sum(vals)) / float(len(vals))
    return avg, len(vals)


def _month_bounds(year, month):
    first = datetime.date(year, month, 1)
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    return first, nxt


def _meeting_present(r):
    """TouchPoint Count column: HeadCount when entered, else recorded attendance.

    Meetings.MaxCount is max(HeadCount, NumPresent). Week at a Glance uses
    MaxCount; the Meetings drill (Count) prefers HeadCount. Regular meetings
    default to head count (RegularMeetingHeadCount = true).
    """
    n = _i(r.HeadCnt) if hasattr(r, 'HeadCnt') else 0
    if n <= 0:
        n = _i(r.PresentCnt) if hasattr(r, 'PresentCnt') else 0
    if n <= 0:
        n = _i(r.MaxCnt) if hasattr(r, 'MaxCnt') else 0
    return n


def _meeting_rows_to_days(rows):
    by_day = {}
    for r in rows or []:
        d = _parse_date(r.MeetDay) if hasattr(r, 'MeetDay') else _parse_date(r.MeetingDate)
        if not d:
            continue
        n = _meeting_present(r)
        if n > 0:
            by_day[d] = by_day.get(d, 0) + n
    out = []
    keys = list(by_day.keys())
    try:
        keys.sort()
    except:
        pass
    for d in keys:
        out.append({'day': d, 'count': by_day[d]})
    return out


def _meeting_days_for_orgs(org_ids, start, end):
    """Meeting attendance on Config involvements (this year / month-over-month)."""
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids or start is None or end is None:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT CAST(m.MeetingDate AS date) AS MeetDay,
    ISNULL(m.MaxCount, 0) AS MaxCnt,
    ISNULL(m.HeadCount, 0) AS HeadCnt,
    ISNULL(m.NumPresent, 0) AS PresentCnt
FROM dbo.Meetings m
WHERE m.OrganizationId IN (""" + frag + """)
AND ISNULL(m.DidNotMeet, 0) = 0
AND m.MeetingDate >= @d1
AND m.MeetingDate < @d2
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('org meetings: ' + _ex_msg(ex))
        return []
    return _meeting_rows_to_days(rows)


def _meetings_for_orgs(org_ids, start, end):
    """Individual meetings for tile drill-down (Week at a Glance → Meetings)."""
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids or start is None or end is None:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT m.MeetingId, m.OrganizationId, o.OrganizationName, m.MeetingDate,
    ISNULL(m.HeadCount, 0) AS HeadCnt,
    ISNULL(m.NumPresent, 0) AS PresentCnt,
    ISNULL(m.MaxCount, 0) AS MaxCnt
FROM dbo.Meetings m
INNER JOIN dbo.Organizations o ON o.OrganizationId = m.OrganizationId
WHERE m.OrganizationId IN (""" + frag + """)
AND ISNULL(m.DidNotMeet, 0) = 0
AND m.MeetingDate >= @d1
AND m.MeetingDate < @d2
ORDER BY m.MeetingDate, o.OrganizationName
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('meeting drill: ' + _ex_msg(ex))
        return []
    out = []
    for r in rows:
        out.append({
            'meeting_id': _i(r.MeetingId),
            'org_id': _i(r.OrganizationId),
            'org_name': _s(r.OrganizationName),
            'when': r.MeetingDate,
            'day': _parse_date(r.MeetingDate),
            'head': _i(r.HeadCnt),
            'recorded': _i(r.PresentCnt),
            'used': _meeting_present(r),
        })
    return out


def _days_from_meetings(meetings):
    by_day = {}
    for m in meetings or []:
        d = m.get('day')
        n = _i(m.get('used'))
        if d and n > 0:
            by_day[d] = by_day.get(d, 0) + n
    out = []
    keys = list(by_day.keys())
    try:
        keys.sort()
    except:
        pass
    for d in keys:
        out.append({'day': d, 'count': by_day[d]})
    return out


def _div_ids_for_orgs(org_ids):
    org_ids = [n for n in (org_ids or []) if _i(n) > 0]
    if not org_ids:
        return []
    frag, names = _sql_in_int(org_ids, 'oid')
    sql = """
SELECT DISTINCT dd.DivId
FROM dbo.DivOrg dd
WHERE dd.OrgId IN (""" + frag + """)
AND ISNULL(dd.DivId, 0) > 0
UNION
SELECT DISTINCT o.DivisionId
FROM dbo.Organizations o
WHERE o.OrganizationId IN (""" + frag + """)
AND ISNULL(o.DivisionId, 0) > 0
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('org divisions: ' + _ex_msg(ex))
        return []
    out = []
    seen = {}
    for r in rows:
        n = _i(r.DivId)
        if n > 0 and n not in seen:
            seen[n] = True
            out.append(n)
    return out


def _awag_div_ids(cfg):
    pinned = _parse_id_list(cfg.get('awag_division_ids'))
    if pinned:
        return pinned
    return _div_ids_for_orgs(_standing_orgs(cfg))


def _meeting_days_for_divs(div_ids, prog_id, start, end):
    """Average Week at a Glance path: Meetings on orgs in Program/Division.

    Last year's involvements still count if they sat in the same Division.
    """
    div_ids = [n for n in (div_ids or []) if _i(n) > 0]
    if not div_ids or start is None or end is None:
        return []
    frag, names = _sql_in_int(div_ids, 'div')
    prog_id = _i(prog_id)
    prog_sql = '1=1'
    p = _dd()
    _bind_ids(p, names)
    if prog_id > 0:
        prog_sql = 'EXISTS (SELECT 1 FROM dbo.ProgDiv pd WHERE pd.DivId = dd.DivId AND pd.ProgId = @prog)'
        p.AddValue('prog', prog_id)
    sql = """
SELECT CAST(m.MeetingDate AS date) AS MeetDay,
    ISNULL(m.MaxCount, 0) AS MaxCnt,
    ISNULL(m.HeadCount, 0) AS HeadCnt,
    ISNULL(m.NumPresent, 0) AS PresentCnt
FROM dbo.Meetings m
WHERE ISNULL(m.DidNotMeet, 0) = 0
AND m.MeetingDate >= @d1
AND m.MeetingDate < @d2
AND (ISNULL(m.HeadCount, 0) > 0 OR ISNULL(m.NumPresent, 0) > 0)
AND EXISTS (
    SELECT 1
    FROM dbo.DivOrg dd
    WHERE dd.OrgId = m.OrganizationId
    AND dd.DivId IN (""" + frag + """)
    AND """ + prog_sql + """
)
"""
    p.AddValue('d1', _ymd(start))
    p.AddValue('d2', _ymd(end))
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('division meetings: ' + _ex_msg(ex))
        return []
    return _meeting_rows_to_days(rows)


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
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.Attend a
INNER JOIN dbo.People pe ON pe.PeopleId = a.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
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


def _sunday_for_date(d):
    """dbo.SundayForDate — Sunday on or before d (Average Week at a Glance)."""
    if d is None:
        return None
    return _add_days(d, -((d.weekday() + 1) % 7))


def _awag_week_vals(days, start, end):
    """Sunday-week present totals in [start, end). Empty weeks stay in the list."""
    if not start or not end or start >= end:
        return []
    sun = _sunday_for_date(start)
    if sun < start:
        sun = _add_days(sun, 7)
    rows = []
    while sun < end:
        w1 = sun
        w2 = _add_days(sun, 7)
        if w1 < start:
            w1 = start
        if w2 > end:
            w2 = end
        n = _week_present_total(days, w1, w2)
        rows.append({'sunday': sun, 'start': w1, 'end': w2, 'count': n, 'included': n > 0})
        sun = _add_days(sun, 7)
    return rows


def _awag_average(days, start, end):
    """Average Week at a Glance (Involvement > Reports > ChurchAttendance2).

    Sundays in [start, end) from SundayForDate. Each week sums present on
    [Sunday, next Sunday), clipped to the range. Weeks with 0 present are
    skipped. Year-over-year uses this window shifted 364 days (52 weeks).
    """
    included = []
    for row in _awag_week_vals(days, start, end):
        if row.get('included'):
            included.append(_i(row.get('count')))
    if not included:
        return 0.0, 0
    return float(sum(included)) / float(len(included)), len(included)


def _month_weekly_average(days, year, month, dow):
    """Mean of weekly present totals that fall in this calendar month."""
    first, nxt = _month_bounds(year, month)
    return _awag_average(days, first, nxt)


def _attendance_bundle(cfg):
    orgs = _standing_orgs(cfg)
    dow = _cfg_i(cfg, 'week_start_dow')
    if dow <= 0 and dow != 0:
        dow = 2
    today = _today()
    this_ws = _week_start(today, dow)
    last_ws = _add_days(this_ws, -7)
    ly_ws = _add_days(this_ws, -364)
    this_end = _add_days(today, 1)
    prev_m = today.month - 1
    prev_y = today.year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    prev2_m = prev_m - 1
    prev2_y = prev_y
    if prev2_m < 1:
        prev2_m = 12
        prev2_y -= 1
    this_first = datetime.date(today.year, today.month, 1)
    last_first, last_next = _month_bounds(prev_y, prev_m)
    prev2_first, prev2_next = _month_bounds(prev2_y, prev2_m)
    ly_this_first = _add_years(this_first, -1)
    ly_this_end = _add_years(this_end, -1)
    ly_last_first = _add_years(last_first, -1)
    ly_last_next = _add_years(last_next, -1)
    ay_start = _academic_year_start(today)
    fq_specs = _academic_fq_specs(today)

    org_start = last_ws
    if prev2_first < org_start:
        org_start = prev2_first
    if ay_start < org_start:
        org_start = ay_start
    ms_oid = _cfg_i(cfg, 'ms_orgid')
    hs_oid = _cfg_i(cfg, 'hs_orgid')
    ms_days = _meeting_days_for_orgs([ms_oid], org_start, this_end) if ms_oid > 0 else []
    hs_days = _meeting_days_for_orgs([hs_oid], org_start, this_end) if hs_oid > 0 else []
    org_days = _merge_meeting_days(ms_days, hs_days)
    this_c = _week_present_total(org_days, this_ws, _add_days(this_ws, 7))
    last_c = _week_present_total(org_days, last_ws, this_ws)
    this_avg, this_n = _awag_average(org_days, this_first, this_end)
    last_avg, last_n = _awag_average(org_days, last_first, last_next)
    prev2_avg, prev2_n = _awag_average(org_days, prev2_first, prev2_next)
    fq_rows = []
    for fid, key, sub, start, end in fq_specs:
        if start >= this_end:
            fq_rows.append({'id': fid, 'key': key, 'sub': sub, 'avg': None, 'weeks': 0})
        else:
            use_end = end
            if use_end > this_end:
                use_end = this_end
            avg, n = _awag_average(org_days, start, use_end)
            fq_rows.append({'id': fid, 'key': key, 'sub': sub, 'avg': avg, 'weeks': n})
    ms_avg, ms_n = _awag_average(ms_days, this_first, this_end)
    hs_avg, hs_n = _awag_average(hs_days, this_first, this_end)
    ms_last_avg, ms_last_n = _awag_average(ms_days, last_first, last_next)
    hs_last_avg, hs_last_n = _awag_average(hs_days, last_first, last_next)
    ms_prev2_avg, ms_prev2_n = _awag_average(ms_days, prev2_first, prev2_next)
    hs_prev2_avg, hs_prev2_n = _awag_average(hs_days, prev2_first, prev2_next)

    div_ids = _awag_div_ids(cfg)
    prog_id = _cfg_i(cfg, 'next_gen_program_id') or NEXT_GEN_PROGRAM_ID
    div_start = ly_ws
    if ly_this_first < div_start:
        div_start = ly_this_first
    if ly_last_first < div_start:
        div_start = ly_last_first
    div_days = _meeting_days_for_divs(div_ids, prog_id, div_start, this_end)
    ly_c = _week_present_total(div_days, ly_ws, _add_days(ly_ws, 7))
    ly_avg, ly_n = _awag_average(div_days, ly_this_first, ly_this_end)
    ly_last_avg, ly_last_n = _awag_average(div_days, ly_last_first, ly_last_next)

    this_first_b, this_next_b = _month_bounds(today.year, today.month)
    this_unique = _attend_unique_count(orgs, this_first_b, this_next_b)
    last_unique = _attend_unique_count(orgs, last_first, last_next)
    ms_unique = _attend_unique_count([ms_oid], this_first_b, this_next_b) if ms_oid > 0 else 0
    hs_unique = _attend_unique_count([hs_oid], this_first_b, this_next_b) if hs_oid > 0 else 0
    ms_last_unique = _attend_unique_count([ms_oid], last_first, last_next) if ms_oid > 0 else 0
    hs_last_unique = _attend_unique_count([hs_oid], last_first, last_next) if hs_oid > 0 else 0
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
        'last_month_delta': last_avg - prev2_avg,
        'last_month_yoy': last_avg - ly_last_avg,
        'week_start': this_ws,
        'week_end': _add_days(this_ws, 6),
        'month_unique': this_unique,
        'last_month_unique': last_unique,
        'month_weeks': this_n,
        'last_month_weeks': last_n,
        'ly_month_weeks': ly_n,
        'this_week_people': _attend_people(orgs, this_ws, _add_days(this_ws, 7)),
        'ay_start': ay_start,
        'fq': fq_rows,
        'ms_avg': ms_avg,
        'ms_weeks': ms_n,
        'ms_unique': ms_unique,
        'ms_delta': ms_avg - ms_last_avg,
        'ms_last_avg': ms_last_avg,
        'ms_last_weeks': ms_last_n,
        'ms_last_unique': ms_last_unique,
        'ms_last_delta': ms_last_avg - ms_prev2_avg,
        'hs_avg': hs_avg,
        'hs_weeks': hs_n,
        'hs_unique': hs_unique,
        'hs_delta': hs_avg - hs_last_avg,
        'hs_last_avg': hs_last_avg,
        'hs_last_weeks': hs_last_n,
        'hs_last_unique': hs_last_unique,
        'hs_last_delta': hs_last_avg - hs_prev2_avg,
    }


def _event_orgs(cfg):
    """Involvements in Next Gen Program (1112) and optional Division(s).

    TouchPoint stores Program/Division on DivOrg + ProgDiv, not only
    Organizations.DivisionId — OrgSearch uses the same path.
    """
    prog = _cfg_i(cfg, 'event_program_id') or NEXT_GEN_PROGRAM_ID
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
    ISNULL(p.Name, '') AS ProgramName,
    CONVERT(varchar(10), mf.MeetFirst, 23) AS MeetFirst,
    CONVERT(varchar(10), mf.MeetLast, 23) AS MeetLast
FROM dbo.Organizations o
LEFT JOIN dbo.Division d ON o.DivisionId = d.Id
LEFT JOIN dbo.Program p ON d.ProgId = p.Id
LEFT JOIN (
    SELECT m.OrganizationId,
        MIN(m.MeetingDate) AS MeetFirst,
        MAX(m.MeetingDate) AS MeetLast
    FROM dbo.Meetings m
    WHERE ISNULL(m.DidNotMeet, 0) = 0
    GROUP BY m.OrganizationId
) mf ON mf.OrganizationId = o.OrganizationId
WHERE (
    EXISTS (
        SELECT 1
        FROM dbo.DivOrg do
        INNER JOIN dbo.ProgDiv pd ON pd.DivId = do.DivId
        WHERE do.OrgId = o.OrganizationId
        AND pd.ProgId = @prog
    )
    OR EXISTS (
        SELECT 1
        FROM dbo.ProgDiv pd
        WHERE pd.DivId = o.DivisionId
        AND pd.ProgId = @prog
    )
    OR ISNULL(d.ProgId, 0) = @prog
)
"""
    p = _dd()
    p.AddValue('prog', prog)
    if divs:
        frag, names = _sql_in_int(divs, 'div')
        sql += """
AND (
    o.DivisionId IN (""" + frag + """)
    OR EXISTS (
        SELECT 1 FROM dbo.DivOrg do2
        WHERE do2.OrgId = o.OrganizationId
        AND do2.DivId IN (""" + frag + """)
    )
)
"""
        _bind_ids(p, names)
    sql += ' ORDER BY ISNULL(o.FirstMeetingDate, o.CreatedDate) DESC, o.OrganizationName'
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
        meet_first = _parse_date_loose(r.MeetFirst) if hasattr(r, 'MeetFirst') else None
        meet_last = _parse_date_loose(r.MeetLast) if hasattr(r, 'MeetLast') else None
        first = meet_first or _parse_date_loose(r.FirstMeetingDate)
        last = meet_last or _parse_date_loose(r.LastMeetingDate)
        created = _parse_date_loose(r.CreatedDate)
        out.append({
            'id': oid,
            'name': _s(r.OrganizationName),
            'start': first or last or created,
            'first': first,
            'last': last,
            'created': created,
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
    """Ministry-year events: meeting-date overlap, created this FY, or Active with no dates.

    CreatedDate is not treated as a meeting date — orgs built before July 1
    still appear if they have no First/Last meeting or are still Active.
    """
    fy_s, fy_e = _fy_bounds()
    evs = []
    for ev in _event_orgs(cfg):
        first = ev.get('first')
        last = ev.get('last')
        created = ev.get('created')
        status = _i(ev.get('status_id'))
        if first or last:
            begins = first or last
            ends = last or first
            if begins and begins < fy_e and ends and ends >= fy_s:
                evs.append(ev)
            elif begins and fy_s <= begins < fy_e:
                evs.append(ev)
            elif last and fy_s <= last < fy_e:
                evs.append(ev)
            continue
        if created and fy_s <= created < fy_e:
            evs.append(ev)
        elif status == 30:
            evs.append(ev)
    return evs


def _event_roster_counts(org_ids):
    """Leaders vs Members per involvement (MemberType AttendanceType + name)."""
    ids = [n for n in (org_ids or []) if _i(n) > 0]
    out = {}
    for n in ids:
        out[n] = {'leaders': 0, 'members': 0}
    if not ids:
        return out
    frag, names = _sql_in_int(ids, 'oid')
    sql = """
SELECT om.OrganizationId,
    SUM(CASE
            WHEN ISNULL(mt.AttendanceTypeId, 0) = 10
            OR UPPER(LTRIM(RTRIM(ISNULL(mt.Description,'')))) LIKE '%LEADER%'
            THEN 1 ELSE 0 END) AS LeaderCount,
    SUM(CASE
            WHEN ISNULL(mt.AttendanceTypeId, 0) = 10
            OR UPPER(LTRIM(RTRIM(ISNULL(mt.Description,'')))) LIKE '%LEADER%'
            THEN 0
            WHEN ISNULL(mt.AttendanceTypeId, 0) = 30
            OR UPPER(LTRIM(RTRIM(ISNULL(mt.Description,'')))) LIKE '%MEMBER%'
            THEN 1 ELSE 0 END) AS MemberCount
FROM dbo.OrganizationMembers om
LEFT JOIN lookup.MemberType mt ON mt.Id = om.MemberTypeId
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
WHERE om.OrganizationId IN (""" + frag + """)
AND ISNULL(pe.IsDeceased, 0) = 0
GROUP BY om.OrganizationId
"""
    p = _dd()
    _bind_ids(p, names)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('event roster counts: ' + _ex_msg(ex))
        return out
    for r in rows:
        oid = _i(r.OrganizationId)
        if oid in out:
            out[oid]['leaders'] = _i(r.LeaderCount)
            out[oid]['members'] = _i(r.MemberCount)
    return out


def _event_enrollments(cfg, events):
    ids = [ev['id'] for ev in (events or [])]
    if not ids:
        return 0, 0, []
    frag, names = _sql_in_int(ids, 'oid')
    sql = """
SELECT om.PeopleId, om.OrganizationId, o.OrganizationName,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel
FROM dbo.OrganizationMembers om
INNER JOIN dbo.Organizations o ON o.OrganizationId = om.OrganizationId
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
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
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel,
    pe.BirthDay, pe.BirthMonth
FROM dbo.OrganizationMembers om
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
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
        rec['extra'] = _md_display(_i(r.BirthMonth), _i(r.BirthDay))
        out.append(rec)
    return out


def _people_on_divisions(div_ids, prog_id=0):
    """Current members of involvements in these Divisions (Next Gen Program 1112)."""
    div_ids = [n for n in (div_ids or []) if _i(n) > 0]
    if not div_ids:
        return []
    frag, names = _sql_in_int(div_ids, 'div')
    prog_id = _i(prog_id, 0) or NEXT_GEN_PROGRAM_ID
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    """ + _sql_school_select() + """,
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
WHERE o.DivisionId IN (""" + frag + """)
AND ISNULL(d.ProgId, 0) = @prog
AND ISNULL(pe.IsDeceased, 0) = 0
ORDER BY PersonName
"""
    p = _dd()
    _bind_ids(p, names)
    p.AddValue('prog', prog_id)
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('division people: ' + _ex_msg(ex))
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


def _sql_org_in_program(org_alias, div_alias, prog_param):
    """Org is under a Program via DivOrg + ProgDiv, or Division.ProgId."""
    return (
        '(EXISTS (SELECT 1 FROM dbo.DivOrg do_vp '
        'INNER JOIN dbo.ProgDiv pd_vp ON pd_vp.DivId = do_vp.DivId '
        'WHERE do_vp.OrgId = ' + org_alias + '.OrganizationId '
        'AND pd_vp.ProgId = ' + prog_param + ') '
        'OR EXISTS (SELECT 1 FROM dbo.ProgDiv pd_vp2 '
        'WHERE pd_vp2.DivId = ' + org_alias + '.DivisionId '
        'AND pd_vp2.ProgId = ' + prog_param + ') '
        'OR ISNULL(' + div_alias + '.ProgId, 0) = ' + prog_param + ')'
    )


def _serving_outside(cfg):
    standing = _standing_orgs(cfg)
    if not standing:
        return []
    vol_prog = _cfg_i(cfg, 'volunteer_program_id') or VOLUNTEER_PROGRAM_ID
    extra = _parse_id_list(cfg.get('volunteer_extra_orgids'))
    if vol_prog <= 0 and not extra:
        return []
    st_frag, st_names = _sql_in_int(standing, 'st')
    extra_sql = ''
    p = _dd()
    _bind_ids(p, st_names)
    if extra:
        ex_frag, ex_names = _sql_in_int(extra, 'ex')
        extra_sql = ' OR o2.OrganizationId IN (' + ex_frag + ') '
        _bind_ids(p, ex_names)
    prog_sql = '1=0'
    if vol_prog > 0:
        prog_sql = _sql_org_in_program('o2', 'd2', '@vprog')
        p.AddValue('vprog', vol_prog)
    match_sql = '(' + prog_sql + extra_sql + ')'
    sql = """
SELECT DISTINCT
    pe.PeopleId,
    ISNULL(pe.Name2, LTRIM(RTRIM(ISNULL(pe.FirstName,'') + ' ' + ISNULL(pe.LastName,'')))) AS PersonName,
    pe.FirstName, pe.LastName, pe.Age,
    """ + _sql_school_select() + """,
    CASE pe.GenderId WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS GenderLabel,
    ISNULL(gl.Description, 'Unknown') AS GradeLabel,
    ISNULL(STUFF((
        SELECT ', ' + o2.OrganizationName
        FROM dbo.OrganizationMembers om2
        INNER JOIN dbo.Organizations o2 ON o2.OrganizationId = om2.OrganizationId
        LEFT JOIN dbo.Division d2 ON o2.DivisionId = d2.Id
        WHERE om2.PeopleId = pe.PeopleId
        AND om2.OrganizationId NOT IN (""" + st_frag + """)
        AND """ + match_sql + """
        ORDER BY o2.OrganizationName
        FOR XML PATH(''), TYPE
    ).value('.', 'nvarchar(max)'), 1, 2, ''), '') AS Extra
FROM dbo.OrganizationMembers om
INNER JOIN dbo.People pe ON pe.PeopleId = om.PeopleId
LEFT JOIN lookup.GradeLevel gl ON pe.GradeLevelId = gl.Id
""" + _sql_school_join('pe') + """
WHERE om.OrganizationId IN (""" + st_frag + """)
AND ISNULL(pe.IsDeceased, 0) = 0
AND EXISTS (
    SELECT 1
    FROM dbo.OrganizationMembers om2
    INNER JOIN dbo.Organizations o2 ON o2.OrganizationId = om2.OrganizationId
    LEFT JOIN dbo.Division d2 ON o2.DivisionId = d2.Id
    WHERE om2.PeopleId = om.PeopleId
        AND om2.OrganizationId NOT IN (""" + st_frag + """)
        AND """ + match_sql + """
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
    """Config order first (newest at top), then any extra SubGroups found on orgs."""
    names = []
    seen = {}
    for n in _group_name_list(cfg) + _discover_subgroups(_standing_orgs(cfg) + _leader_orgs(cfg)):
        key = n.lower()
        if n and key not in seen:
            seen[key] = True
            names.append(n)
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


def _user_tag_names():
    """Personal tags owned by the signed-in user (TypeId 1)."""
    owner_id = 0
    try:
        owner_id = int(model.UserPeopleId)
    except:
        owner_id = 0
    if owner_id <= 0:
        return []
    p = _dd()
    p.AddValue('uid', owner_id)
    sql = """
SELECT t.Name
FROM dbo.Tag t
WHERE t.PeopleId = @uid
AND t.TypeId = 1
AND LTRIM(RTRIM(ISNULL(t.Name,''))) <> ''
ORDER BY CASE WHEN t.Name LIKE '.%' THEN 1 ELSE 0 END, t.Name
"""
    try:
        rows = list(q.QuerySql(sql, p))
    except Exception, ex:
        _warn('user tags: ' + _ex_msg(ex))
        return []
    names = []
    seen = {}
    for r in rows:
        n = _s(r.Name)
        key = n.lower()
        if n and key not in seen:
            seen[key] = True
            names.append(n)
    return names


def _tag_modal_html():
    names = _user_tag_names()
    has_tags = len(names) > 0
    html = '<div class="tag-modal-overlay" id="tag-modal-overlay">'
    html += '<div class="tag-modal"><div class="tag-modal-header" id="tag-modal-title">Add to Tag</div>'
    html += '<div class="tag-modal-body"><p class="tag-modal-meta" id="tag-modal-count"></p>'
    if has_tags:
        html += '<label class="option-row"><input type="radio" name="tag-source" value="existing" id="tag-source-existing" checked />'
        html += '<span>Use one of my tags</span></label>'
        html += '<div id="tag-existing-wrap" class="tag-source-panel">'
        html += '<select id="tag-existing-select"><option value="">Choose a tag</option>'
        for n in names:
            html += '<option value="' + _html(n) + '">' + _html(n) + '</option>'
        html += '</select></div>'
        html += '<label class="option-row"><input type="radio" name="tag-source" value="new" id="tag-source-new" />'
        html += '<span>Create a new tag</span></label>'
    else:
        html += '<label class="option-row"><input type="radio" name="tag-source" value="new" id="tag-source-new" checked />'
        html += '<span>Create a new tag</span></label>'
    html += '<div id="tag-new-wrap" class="tag-source-panel"'
    if has_tags:
        html += ' style="display:none"'
    html += '>'
    html += '<input type="text" id="tag-name-input" maxlength="50" autocomplete="off" placeholder="New tag name" />'
    html += '</div>'
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
    return html


def _save_config_from_form(cfg):
    if not _is_admin():
        return False, 'Admin only.'
    keys = [
        'ms_orgid', 'hs_orgid', 'sunday_attendance_orgid', 'week_start_dow', 'event_program_id',
        'event_division_ids', 'event_date_extra', 'leaders_orgid', 'student_leaders_orgid',
        'coaches_orgid', 'onboarding_url', 'involvement_dash_url',
        'kw_decision', 'kw_decision_scope', 'kw_stories', 'baptism_scope',
        'next_gen_program_id', 'kids_division_id', 'awana_division_id',
        'senior_year_orgid', 'awag_division_ids',
        'volunteer_program_id', 'volunteer_extra_orgids', 'view_only_role',
        'small_group_names', 'header_logo_url',
    ]
    int_keys = {
        'ms_orgid', 'hs_orgid', 'sunday_attendance_orgid', 'week_start_dow', 'event_program_id',
        'leaders_orgid', 'student_leaders_orgid', 'coaches_orgid',
        'next_gen_program_id', 'kids_division_id', 'awana_division_id',
        'senior_year_orgid', 'volunteer_program_id',
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
    names.insert(0, name)
    cfg['small_group_names'] = ', '.join(names)
    if _is_admin() or _can_write(cfg):
        try:
            _save_config(cfg)
        except:
            pass
    return True, name


def _reorder_group(cfg, name, delta):
    """Move a group up (-1) or down (+1) in Config small_group_names."""
    if not _can_write(cfg):
        return False, 'View only — cannot reorder.'
    name = _s(name)
    names = _all_group_names(cfg)
    idx = -1
    i = 0
    while i < len(names):
        if names[i].lower() == name.lower():
            idx = i
            break
        i += 1
    if idx < 0:
        return False, 'Group not found.'
    nxt = idx + _i(delta)
    if nxt < 0 or nxt >= len(names):
        return True, 'Already at the end.'
    tmp = names[idx]
    names[idx] = names[nxt]
    names[nxt] = tmp
    cfg['small_group_names'] = ', '.join(names)
    try:
        _save_config(cfg)
    except Exception, ex:
        return False, 'Save failed: ' + _ex_msg(ex)
    if _i(delta) < 0:
        return True, 'Moved up.'
    return True, 'Moved down.'
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


def _remove_subgroup(cfg, people_id, group_name):
    if not _can_write(cfg):
        return False, 'View only — cannot remove.'
    people_id = _i(people_id)
    group_name = _s(group_name)
    if not people_id or not group_name:
        return False, 'Person and group are required.'
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
    any_ok = False
    last = ''
    for oid in targets:
        try:
            model.RemoveSubGroup(people_id, oid, group_name)
            any_ok = True
        except Exception, ex:
            last = _ex_msg(ex)
    if any_ok:
        return True, 'Removed from ' + group_name + '.'
    return False, last or 'Could not remove from group.'


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


def _remove_many(cfg, ids_csv, group_name):
    ids = _parse_people_ids(ids_csv)
    if not ids:
        return False, 'Select at least one person.'
    group_name = _s(group_name)
    if not group_name:
        return False, 'Choose a group to remove from.'
    ok_n = 0
    last = ''
    for pid in ids:
        ok, msg = _remove_subgroup(cfg, pid, group_name)
        last = msg
        if ok:
            ok_n += 1
    if ok_n:
        return True, str(ok_n) + ' removed from ' + group_name + '.'
    return False, last or 'No removals.'


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _person_link(person, first_last=False):
    pid = _i(person.get('people_id'))
    if first_last:
        fl = (_s(person.get('first')) + ' ' + _s(person.get('last'))).strip()
        name = _html(fl or person.get('name') or '(Unknown)')
    else:
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
        nshow = _round_half_up(n)
    else:
        nshow = _i(n)
    label = ('+' if nshow > 0 else '') + str(nshow)
    cls = 'delta-flat'
    if nshow > 0:
        cls = 'delta-up'
    elif nshow < 0:
        cls = 'delta-down'
    return '<span class="delta ' + cls + '">' + _html(label) + '</span>'


def _att_drill_href(key):
    return _script_path() + '?view=home&drill=meetings&att=' + _url_enc(key) + '#sm-drill-list'


def _att_drill_spec(cfg, key):
    """title, org_ids, start, end, is_avg for an attendance tile drill."""
    key = _s(key).lower()
    today = _today()
    this_end = _add_days(today, 1)
    this_first = datetime.date(today.year, today.month, 1)
    prev_m = today.month - 1
    prev_y = today.year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    last_first, last_next = _month_bounds(prev_y, prev_m)
    all_orgs = _standing_orgs(cfg)
    ms_oid = _cfg_i(cfg, 'ms_orgid')
    hs_oid = _cfg_i(cfg, 'hs_orgid')
    month_name = today.strftime('%B')
    last_month_name = datetime.date(prev_y, prev_m, 1).strftime('%B')
    dow = _cfg_i(cfg, 'week_start_dow')
    if dow <= 0 and dow != 0:
        dow = 2
    this_ws = _week_start(today, dow)
    specs = {
        'week': ('This week present', all_orgs, this_ws, _add_days(this_ws, 7), False),
        'last_month': (last_month_name + ' avg attendance', all_orgs, last_first, last_next, True),
        'month': (month_name + ' avg attendance', all_orgs, this_first, this_end, True),
        'ms_last': ('Middle School · ' + last_month_name, [ms_oid], last_first, last_next, True),
        'ms_month': ('Middle School · ' + month_name, [ms_oid], this_first, this_end, True),
        'hs_last': ('High School · ' + last_month_name, [hs_oid], last_first, last_next, True),
        'hs_month': ('High School · ' + month_name, [hs_oid], this_first, this_end, True),
    }
    for fid, label, sub, start, end in _academic_fq_specs(today):
        use_end = end
        if use_end > this_end:
            use_end = this_end
        specs[fid] = (label + ' · ' + sub + ' avg attendance', all_orgs, start, use_end, True)
    return specs.get(key)


def _meetings_drill_html(cfg, key):
    spec = _att_drill_spec(cfg, key)
    if not spec:
        return '<div class="empty-state">Unknown attendance drill.</div>'
    title, orgs, start, end, is_avg = spec
    meetings = _meetings_for_orgs(orgs, start, end)
    days = _days_from_meetings(meetings)
    last_day = _add_days(end, -1) if end else end
    html = '<p class="meta-line">' + _html(_date_display(start)) + ' – ' + _html(_date_display(last_day))
    html += ' · Used in Avg = Head Count when entered, else Recorded Attendance. Empty weeks are skipped.</p>'
    if is_avg:
        weeks = _awag_week_vals(days, start, end)
        included = []
        for w in weeks:
            if w.get('included'):
                included.append(_i(w.get('count')))
        n = len(included)
        if n > 0:
            avg_s = str(_round_half_up(float(sum(included)) / float(n)))
        else:
            avg_s = '—'
        html += '<div class="table-scroll"><table class="people-table"><thead><tr>'
        html += '<th>Week (Sunday)</th><th class="num">Present</th><th>In average</th></tr></thead><tbody>'
        if not weeks:
            html += '<tr><td colspan="3">No weeks in this range.</td></tr>'
        for w in weeks:
            html += '<tr><td>' + _html(_date_display(w.get('sunday'))) + '</td>'
            html += '<td class="num">' + str(_i(w.get('count'))) + '</td>'
            html += '<td>' + ('Yes' if w.get('included') else 'Skipped (0)') + '</td></tr>'
        html += '</tbody><tfoot><tr><td><strong>Average</strong></td>'
        html += '<td class="num"><strong>' + avg_s + '</strong></td>'
        html += '<td>' + str(n) + ' week' + ('s' if n != 1 else '') + '</td></tr></tfoot></table></div>'
    html += '<div class="list-actions"><p class="meta-line" style="margin:0"><strong>'
    html += str(len(meetings)) + '</strong> meetings · click a header to sort</p></div>'
    html += '<div class="table-scroll"><table class="people-table sm-sortable"><thead><tr>'
    html += '<th class="sm-sort" data-sort="text">Meeting</th>'
    html += '<th class="sm-sort" data-sort="text">Involvement</th>'
    html += '<th class="sm-sort num" data-sort="num">Head Count</th>'
    html += '<th class="sm-sort num" data-sort="num">Recorded Attendance</th>'
    html += '<th class="sm-sort num" data-sort="num">Used in Avg</th></tr></thead><tbody>'
    head_sum = 0
    rec_sum = 0
    used_sum = 0
    if not meetings:
        html += '<tr><td colspan="5">No meetings in this range.</td></tr>'
    for m in meetings:
        head_sum += _i(m.get('head'))
        rec_sum += _i(m.get('recorded'))
        used_sum += _i(m.get('used'))
        mid = _i(m.get('meeting_id'))
        oid = _i(m.get('org_id'))
        when = _html(_dt_display(m.get('when')))
        html += '<tr>'
        if mid > 0:
            html += '<td><a href="/Meeting/' + str(mid) + '" target="_blank" rel="noopener">' + when + '</a></td>'
        else:
            html += '<td>' + when + '</td>'
        orgn = _html(m.get('org_name'))
        if oid > 0:
            html += '<td><a href="/Org/' + str(oid) + '" target="_blank" rel="noopener">' + orgn + '</a></td>'
        else:
            html += '<td>' + orgn + '</td>'
        html += '<td class="num">' + str(_i(m.get('head'))) + '</td>'
        html += '<td class="num">' + str(_i(m.get('recorded'))) + '</td>'
        html += '<td class="num">' + str(_i(m.get('used'))) + '</td></tr>'
    html += '</tbody>'
    if meetings:
        html += '<tfoot><tr><td colspan="2"><strong>Total</strong></td>'
        html += '<td class="num"><strong>' + str(head_sum) + '</strong></td>'
        html += '<td class="num"><strong>' + str(rec_sum) + '</strong></td>'
        html += '<td class="num"><strong>' + str(used_sum) + '</strong></td></tr></tfoot>'
    html += '</table></div>'
    return html


def _month_avg_card(avg, weeks, label, unique, delta, href=''):
    if _i(weeks) <= 0:
        val = '—'
    else:
        val = _avg_label(avg, weeks)
    if href:
        html = '<a class="stat-card" href="' + href + '">'
    else:
        html = '<div class="stat-card">'
    html += '<div class="stat-value">' + val + '</div>'
    html += '<div class="stat-label">' + _html(label) + '</div>'
    html += '<div class="stat-sub"><span class="unique-count">' + str(_i(unique)) + '</span> unique · vs last mo '
    html += _delta_html(delta, 'float') + '</div>'
    if href:
        html += '</a>'
    else:
        html += '</div>'
    return html


def _filter_people(people, grade='', gender='', q=''):
    grade = _s(grade).lower()
    gender = _s(gender).lower()
    q = _s(q).lower()
    out = []
    for p in people or []:
        if grade:
            pg = _s(p.get('grade'))
            if pg.lower() != grade:
                gk = _grade_key(pg)
                fk = _grade_key(grade)
                if not gk or gk != fk:
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


def _roster_table(people, extra_label='', can_write=False, tag_suggest='Student Ministry', show_groups=False, show_extra=False, checkboxes=False, show_grade=True, show_school=True):
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
    if show_grade:
        html += '<th class="sm-sort" data-sort="text">Grade</th>'
    html += '<th class="sm-sort" data-sort="text">Gender</th>'
    html += '<th class="sm-sort" data-sort="num">Age</th>'
    if show_school:
        html += '<th class="sm-sort" data-sort="text">School District</th>'
    if show_groups:
        html += '<th class="sm-sort" data-sort="text">Groups</th>'
    if show_extra:
        html += '<th class="sm-sort" data-sort="text">' + _html(extra_label or 'Detail') + '</th>'
    html += '</tr></thead><tbody>'
    cols = 3 + (1 if checkboxes else 0) + (1 if show_grade else 0) + (1 if show_school else 0)
    cols += (1 if show_groups else 0) + (1 if show_extra else 0)
    if not people:
        html += '<tr><td colspan="' + str(cols) + '"><div class="empty-state">No people</div></td></tr>'
    for p in people or []:
        html += '<tr>'
        if checkboxes:
            html += '<td><input type="checkbox" class="sm-row-check" name="pid" value="' + str(_i(p.get('people_id'))) + '" /></td>'
        html += '<td>' + _person_link(p) + '</td>'
        if show_grade:
            html += '<td>' + _html(p.get('grade')) + '</td>'
        html += '<td>' + _html(p.get('gender')) + '</td>'
        html += '<td>' + _html(p.get('age')) + '</td>'
        if show_school:
            html += '<td>' + _html(p.get('school')) + '</td>'
        if show_groups:
            html += '<td>' + _html(p.get('groups')) + '</td>'
        if show_extra:
            html += '<td>' + _html(p.get('extra')) + '</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


def _breakdown_cards(counts, view, key_name, title='', anchor='', ordered=None, gray=False):
    """Tiles for a breakdown. ordered = list of (href_label, display_label, n)."""
    if ordered is None:
        items = []
        for label, n in counts.items():
            items.append((_s(label), _s(label), _i(n)))
        try:
            items.sort(key=lambda x: (-x[2], x[1].lower()))
        except:
            pass
    else:
        items = ordered
    grid = '<div class="stats-grid demo-grid">'
    if not items:
        grid += '<div class="stat-card"><div class="stat-label">No data</div>'
        grid += '<div class="stat-value">0</div></div>'
    for href_label, display, n in items:
        href = _script_path() + '?view=' + view + '&' + key_name + '=' + model.UrlEncode(_s(href_label)) + '#sm-filtered-list'
        grid += '<a class="stat-card link-card" href="' + href + '">'
        grid += '<div class="stat-label">' + _html(display) + '</div>'
        grid += '<div class="stat-value">' + str(_i(n)) + '</div></a>'
    grid += '</div>'
    if not title:
        return grid
    cls = 'demo-row'
    if gray:
        cls += ' home-band home-band-b'
    html = '<div class="' + cls + '"'
    if anchor:
        html += ' id="' + _html(anchor) + '"'
    html += '>'
    html += '<button type="button" class="demo-row-caret" aria-expanded="true">'
    html += '<span class="demo-row-title">' + _html(title) + '</span>'
    html += '<i class="fa fa-caret-up" aria-hidden="true"></i></button>'
    html += '<div class="demo-row-body">' + grid + '</div></div>'
    return html


def _grade_nth(n):
    return str(_i(n)) + 'th'


def _grade_tile_items(counts, nums):
    """Fixed-order grade tiles. Display 6th…12th; href uses the live grade label."""
    by_n = {}
    for label, c in (counts or {}).items():
        k = _grade_key(label)
        if k not in nums:
            continue
        if k not in by_n:
            by_n[k] = [_s(label), 0]
        by_n[k][1] += _i(c)
    out = []
    for n in nums:
        disp = _grade_nth(n)
        if n in by_n:
            out.append((by_n[n][0], disp, by_n[n][1]))
        else:
            out.append((disp, disp, 0))
    return out


def _grade_section(counts):
    html = '<div id="sm-demo-grade">'
    html += _breakdown_cards(
        counts, 'demographics', 'grade', 'Middle School', '',
        _grade_tile_items(counts, [6, 7, 8]), True)
    html += _breakdown_cards(
        counts, 'demographics', 'grade', 'High School', '',
        _grade_tile_items(counts, [9, 10, 11, 12]))
    html += '</div>'
    return html


def _pie_point(cx, cy, r, deg):
    rad = (deg * math.pi) / 180.0
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _pie_slice_path(cx, cy, r, start_deg, end_deg):
    sweep = end_deg - start_deg
    if sweep <= 0.05:
        return ''
    if sweep >= 359.95:
        return (
            'M ' + ('%.2f' % cx) + ' ' + ('%.2f' % (cy - r))
            + ' a ' + ('%.2f' % r) + ' ' + ('%.2f' % r) + ' 0 1 1 0 ' + ('%.2f' % (2 * r))
            + ' a ' + ('%.2f' % r) + ' ' + ('%.2f' % r) + ' 0 1 1 0 -' + ('%.2f' % (2 * r))
        )
    x0, y0 = _pie_point(cx, cy, r, start_deg)
    x1, y1 = _pie_point(cx, cy, r, end_deg)
    large = 1 if sweep > 180 else 0
    return (
        'M ' + ('%.2f' % cx) + ' ' + ('%.2f' % cy)
        + ' L ' + ('%.2f' % x0) + ' ' + ('%.2f' % y0)
        + ' A ' + ('%.2f' % r) + ' ' + ('%.2f' % r) + ' 0 ' + str(large) + ' 1 '
        + ('%.2f' % x1) + ' ' + ('%.2f' % y1) + ' Z'
    )


def _school_pie(counts):
    """SVG pie for School District. Slices use Navy / Artisan family colors."""
    items = list((counts or {}).items())
    try:
        items.sort(key=lambda x: (-_i(x[1]), _s(x[0]).lower()))
    except:
        pass
    total = 0
    for _label, n in items:
        total += _i(n)
    colors = [
        BRAND['navy'], BRAND['artisan'], '#3D5A73', '#C46B68',
        '#6B8499', '#E89A97', '#1C3348', '#A34441', '#8FA3B5', '#F0B3B1',
    ]
    html = '<div class="demo-pie-wrap">'
    if total <= 0:
        html += '<div class="empty-state">No school district data</div></div>'
        return html
    cx, cy, r = 100.0, 100.0, 88.0
    html += '<svg class="demo-pie" viewBox="0 0 200 200" role="img" aria-label="School District">'
    angle = -90.0
    i = 0
    legend = '<ul class="demo-pie-legend">'
    for label, n in items:
        n = _i(n)
        if n <= 0:
            continue
        sweep = 360.0 * float(n) / float(total)
        color = colors[i % len(colors)]
        d = _pie_slice_path(cx, cy, r, angle, angle + sweep)
        href = _script_path() + '?view=demographics&school=' + model.UrlEncode(_s(label)) + '#sm-filtered-list'
        pct = int(round(100.0 * float(n) / float(total)))
        tip = _html(label) + ' · ' + str(n) + ' (' + str(pct) + '%)'
        if d:
            html += '<a href="' + href + '"><path d="' + d + '" fill="' + color + '">'
            html += '<title>' + tip + '</title></path></a>'
        legend += '<li><a href="' + href + '"><span class="demo-swatch" style="background:' + color + '"></span>'
        legend += '<span class="demo-pie-name">' + _html(label) + '</span>'
        legend += '<span class="demo-pie-n">' + str(n) + ' · ' + str(pct) + '%</span></a></li>'
        angle += sweep
        i += 1
    html += '</svg>'
    legend += '</ul>'
    html += legend + '</div>'
    return html


def _school_district_block(counts):
    tiles = _breakdown_cards(counts, 'demographics', 'school', '')
    html = '<div class="demo-row home-band home-band-b" id="sm-demo-schools">'
    html += '<button type="button" class="demo-row-caret" aria-expanded="true">'
    html += '<span class="demo-row-title">School District</span>'
    html += '<i class="fa fa-caret-up" aria-hidden="true"></i></button>'
    html += '<div class="demo-row-body">' + tiles + _school_pie(counts) + '</div></div>'
    return html


def _demo_subnav(items=None, aria='Demographics sections'):
    if not items:
        items = [
            ('sm-demo-grade', 'Grade'),
            ('sm-demo-schools', 'School Districts'),
            ('sm-demo-birthdays', 'Birthdays'),
            ('sm-filtered-list', 'Master Roster'),
        ]
    html = '<nav class="subtabs demo-subnav" aria-label="' + _html(aria) + '">'
    for aid, label in items:
        html += '<a class="dash-tab demo-jump" href="#' + aid + '">' + _html(label) + '</a>'
    html += '</nav>'
    return html


def _header_hero_html(cfg):
    """Refuge Students logo on the Downriver header."""
    url = _s((cfg or {}).get('header_logo_url')) or HEADER_LOGO_URL
    if not url:
        return ''
    html = '<div class="sm-header-hero">'
    html += '<img src="' + _html(url) + '" alt="' + _html(APP_TITLE) + '" />'
    html += '</div>'
    return html


def _nav_tabs_html(view, tabs, is_admin):
    html = ''
    for key, label in tabs:
        if key == 'config' and not is_admin:
            continue
        cls = 'dash-tab' + (' active' if key == view else '')
        html += '<a class="' + cls + '" href="' + _script_path() + '?view=' + key + '">' + _html(label) + '</a>'
    return html


def _nav(view, is_admin):
    html = '<nav class="dash-nav" id="sm-dash-nav" aria-label="' + _html(APP_TITLE) + '">'
    html += '<button type="button" class="dash-nav-caret" id="sm-nav-caret" aria-expanded="true" title="Collapse menu">'
    html += '<i class="fa fa-caret-up" aria-hidden="true"></i></button>'
    html += '<div class="dash-nav-body">'
    html += '<div class="dash-nav-segment"><div class="dash-tabs">'
    html += _nav_tabs_html(view, NAV_TABS_TOP, is_admin)
    html += '</div></div>'
    html += '<div class="dash-nav-segment"><div class="dash-tabs">'
    html += _nav_tabs_html(view, NAV_TABS_MAIN, is_admin)
    html += '</div></div>'
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
    stories = _people_with_keywords([_s(cfg.get('kw_stories'))], True, cfg)
    events = _fy_events(cfg)
    uniq, raw, enroll_people = _event_enrollments(cfg, events)
    fy_unique_attends = _attend_unique_count(_standing_orgs(cfg), fy_s, fy_e)
    if fy_unique_attends > 0:
        engaged_pct = int(round(100.0 * float(uniq) / float(fy_unique_attends)))
        engaged_label = str(engaged_pct) + '%'
    else:
        engaged_label = '—'
    sun_oid = _cfg_i(cfg, 'sunday_attendance_orgid') or SUNDAY_ATTEND_ORGID
    sun_avg, sun_n = _sunday_headcount_average(sun_oid, fy_s, fy_e)
    if sun_avg > 0:
        sunday_pct = int(round(100.0 * float(fy_unique_attends) / sun_avg))
        sunday_pct_label = str(sunday_pct) + '%'
    else:
        sunday_pct_label = '—'
    roster_counts = _event_roster_counts([ev['id'] for ev in events])
    serving = _serving_outside(cfg)
    today = _today()
    month_name = today.strftime('%B')
    prev_m = today.month - 1
    prev_y = today.year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    last_month_name = datetime.date(prev_y, prev_m, 1).strftime('%B')
    html = '<div class="cover-head cover-head-center"><h2>Metrics &amp; Performance</h2>'
    html += '<p class="meta-line">Ministry year ' + _html(_date_display(fy_s)) + ' – ' + _html(_date_display(_add_days(fy_e, -1))) + '</p></div>'
    html += _demo_subnav(
        [('sm-home-attendance', 'Attendance'), ('sm-home-milestones', 'Milestones'),
        ('sm-home-leaders', 'Leadership'), ('sm-home-events', 'Events')],
        'Home sections')
    html += '<div class="home-band home-band-b" id="sm-home-attendance">'
    html += '<div class="home-row">'
    html += '<h3 class="home-row-title home-row-title-artisan">Attendance</h3>'
    html += '<div class="stats-grid home-row-att">'
    html += '<a class="stat-card" href="' + _att_drill_href('week') + '">'
    html += '<div class="stat-value">' + str(att['this_week']) + '</div>'
    html += '<div class="stat-label">This week present</div>'
    html += '<div class="stat-sub">WoW ' + _delta_html(att['wow']) + ' · LY week ' + _delta_html(att['yoy_week']) + '</div></a>'
    html += '<div class="home-month-col">'
    html += '<h4 class="home-month-title">' + _html(last_month_name) + '</h4>'
    html += '<a class="stat-card" href="' + _att_drill_href('last_month') + '">'
    html += '<div class="stat-value">' + _avg_label(att['last_month_avg']) + '</div>'
    html += '<div class="stat-label">Last month avg attendance</div>'
    html += '<div class="stat-sub"><span class="unique-count">' + str(_i(att.get('last_month_unique'))) + '</span> unique · vs last mo '
    html += _delta_html(att.get('last_month_delta'), 'float')
    html += ' · vs LY ' + _delta_html(att.get('last_month_yoy'), 'float') + '</div></a>'
    html += '</div>'
    html += '<div class="home-month-col">'
    html += '<h4 class="home-month-title">' + _html(month_name) + '</h4>'
    html += '<a class="stat-card" href="' + _att_drill_href('month') + '">'
    html += '<div class="stat-value">' + _avg_label(att['month_avg']) + '</div>'
    html += '<div class="stat-label">Month avg attendance</div>'
    html += '<div class="stat-sub"><span class="unique-count">' + str(_i(att.get('month_unique'))) + '</span> unique · vs last mo '
    html += _delta_html(att['month_delta'], 'float')
    html += ' · vs LY ' + _delta_html(att['month_yoy'], 'float') + '</div></a>'
    html += '</div>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=fy_unique#sm-drill-list">'
    html += '<div class="stat-value">' + sunday_pct_label + '</div>'
    html += '<div class="stat-label">Percent of Sunday Attendance</div>'
    html += '<div class="stat-sub"><span class="unique-count">' + str(fy_unique_attends) + '</span> unique / '
    html += ('%.0f' % float(sun_avg)) + ' avg In-Person Sunday (FY) · ' + str(sun_n) + ' Sundays</div></a>'
    html += '</div>'
    html += '<div class="stats-grid home-row-level">'
    html += '<div class="home-level-col">'
    html += '<h4 class="home-level-title">Middle School</h4>'
    html += '<div class="stats-grid home-row-level-months">'
    html += '<div class="home-month-col"><h4 class="home-month-title">' + _html(last_month_name) + '</h4>'
    html += _month_avg_card(att.get('ms_last_avg'), att.get('ms_last_weeks'),
        'Last month avg attendance', att.get('ms_last_unique'),
        att.get('ms_last_delta'), _att_drill_href('ms_last'))
    html += '</div>'
    html += '<div class="home-month-col"><h4 class="home-month-title">' + _html(month_name) + '</h4>'
    html += _month_avg_card(att.get('ms_avg'), att.get('ms_weeks'),
        'Month avg attendance', att.get('ms_unique'),
        att.get('ms_delta'), _att_drill_href('ms_month'))
    html += '</div></div></div>'
    html += '<div class="home-level-col">'
    html += '<h4 class="home-level-title">High School</h4>'
    html += '<div class="stats-grid home-row-level-months">'
    html += '<div class="home-month-col"><h4 class="home-month-title">' + _html(last_month_name) + '</h4>'
    html += _month_avg_card(att.get('hs_last_avg'), att.get('hs_last_weeks'),
        'Last month avg attendance', att.get('hs_last_unique'),
        att.get('hs_last_delta'), _att_drill_href('hs_last'))
    html += '</div>'
    html += '<div class="home-month-col"><h4 class="home-month-title">' + _html(month_name) + '</h4>'
    html += _month_avg_card(att.get('hs_avg'), att.get('hs_weeks'),
        'Month avg attendance', att.get('hs_unique'),
        att.get('hs_delta'), _att_drill_href('hs_month'))
    html += '</div></div></div>'
    html += '</div>'
    html += '<div class="fq-block demo-row is-collapsed">'
    html += '<button type="button" class="demo-row-caret fq-caret" aria-expanded="false">'
    html += '<span class="fq-title">Academic Year FQ Averages</span>'
    html += '<i class="fa fa-caret-down" aria-hidden="true"></i></button>'
    html += '<div class="demo-row-body stats-grid home-row-fq">'
    for fq in (att.get('fq') or []):
        n = _i(fq.get('weeks'))
        avg = fq.get('avg')
        if avg is None or n <= 0:
            val = '—'
        else:
            val = _avg_label(avg, n)
        html += '<a class="stat-card" href="' + _att_drill_href(_s(fq.get('id') or fq.get('key')).lower()) + '">'
        html += '<div class="stat-label">' + _html(fq.get('key')) + '</div>'
        html += '<div class="stat-value">' + val + '</div>'
        html += '<div class="stat-sub">Academic year · ' + _html(fq.get('sub')) + '</div></a>'
    html += '</div></div>'
    html += '<p class="meta-line">Week of ' + _html(_date_display(att['week_start'])) + ' – ' + _html(_date_display(att['week_end'])) + '</p>'
    html += '</div></div>'

    html += '<div class="home-band home-band-navy" id="sm-home-milestones">'
    html += '<div class="home-row">'
    html += '<div class="cover-head cover-head-center"><h2>Milestones</h2></div>'
    html += '<div class="stats-grid home-row-hero">'
    html += '<a class="stat-card stat-hero" href="' + _script_path() + '?view=home&drill=decisions#sm-drill-list">'
    html += '<div class="stat-value">' + str(len(decisions)) + '</div>'
    html += '<div class="stat-label">Decisions</div></a>'
    html += '<a class="stat-card stat-hero" href="' + _script_path() + '?view=home&drill=baptisms#sm-drill-list">'
    html += '<div class="stat-value">' + str(len(baptisms)) + '</div>'
    html += '<div class="stat-label">Baptisms</div></a>'
    html += '<a class="stat-card stat-hero" href="' + _script_path() + '?view=home&drill=stories#sm-drill-list">'
    html += '<div class="stat-value">' + str(len(stories)) + '</div>'
    html += '<div class="stat-label">Stories of Transformation</div></a>'
    html += '</div></div></div>'

    html += '<div class="home-band home-band-a" id="sm-home-leaders">'
    html += '<div class="home-row">'
    html += '<h3 class="home-row-title">Leaders</h3>'
    html += '<div class="stats-grid home-row-leaders">'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=leaders#sm-vol-leaders">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'leaders_orgid'))) + '</div>'
    html += '<div class="stat-label">SG Leaders</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=coaches#sm-vol-coaches">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'coaches_orgid'))) + '</div>'
    html += '<div class="stat-label">SG Coaches</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=students#sm-vol-students">'
    html += '<div class="stat-value">' + str(_org_member_count(_cfg_i(cfg, 'student_leaders_orgid'))) + '</div>'
    html += '<div class="stat-label">Student Lead Team</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=campus#sm-vol-campus">'
    html += '<div class="stat-value">—</div>'
    html += '<div class="stat-label">Campus Ministry</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=volunteers&list=serving#sm-serving-beyond">'
    html += '<div class="stat-value">' + str(len(serving)) + '</div>'
    html += '<div class="stat-label">Students Serving Beyond Refuge</div></a>'
    html += '</div></div></div>'

    html += '<div class="home-band home-band-b" id="sm-home-events">'
    html += '<div class="home-row">'
    html += '<h3 class="home-row-title">Events</h3>'
    html += '<div class="stats-grid home-row-events">'
    html += '<div class="stat-card"><div class="stat-label">Events since July 1</div>'
    html += '<div class="stat-value">' + str(len(events)) + '</div></div>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=enroll_unique#sm-drill-list">'
    html += '<div class="stat-label">Unique event enrollments</div>'
    html += '<div class="stat-value">' + str(uniq) + '</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=enroll_raw#sm-drill-list">'
    html += '<div class="stat-label">Raw event enrollments</div>'
    html += '<div class="stat-value">' + str(raw) + '</div></a>'
    html += '<a class="stat-card" href="' + _script_path() + '?view=home&drill=enroll_unique#sm-drill-list">'
    html += '<div class="stat-label">Percent Engaged in Events</div>'
    html += '<div class="stat-value">' + engaged_label + '</div>'
    html += '<div class="stat-sub"><span class="unique-count">' + str(uniq) + '</span> unique enrollments / '
    html += '<span class="unique-count">' + str(fy_unique_attends) + '</span> unique attends (FY)</div></a>'
    html += '</div></div>'

    dash = _s(cfg.get('involvement_dash_url')) or '/PyScriptForm/InvolvementDashboard'
    html += '<div class="vbs-card"><h3>Ministry-year events</h3>'
    html += '<p class="meta-line">Past events are grey. Upcoming / in-progress are Navy. When is first–last meeting date. Name opens the involvement; icon opens Involvement Dashboard.</p>'
    html += '<div class="table-scroll"><table class="people-table sm-sortable"><thead><tr>'
    html += '<th class="sm-sort" data-sort="text">Event</th>'
    html += '<th class="sm-sort" data-sort="text">When</th>'
    html += '<th class="sm-sort" data-sort="num">Leaders</th>'
    html += '<th class="sm-sort" data-sort="num">Members</th>'
    html += '<th></th></tr></thead><tbody>'
    if not events:
        html += '<tr><td colspan="5"><div class="empty-state">No events in Program 1112 / Division 46 this ministry year. Confirm those Ids on Config, then Refresh.</div></td></tr>'
    ordered = list(events or [])
    def _ev_when_key(ev):
        d = ev.get('start') or ev.get('last') or ev.get('created')
        if d:
            return d
        return datetime.date(1, 1, 1)
    try:
        ordered.sort(key=_ev_when_key, reverse=True)
    except:
        pass
    for ev in ordered:
        past_cls = ' event-past' if _event_is_past(ev) else ' event-upcoming'
        when = _when_display(ev)
        counts = roster_counts.get(ev['id']) or {}
        html += '<tr class="' + past_cls + '">'
        html += '<td><a href="/Org/' + str(ev['id']) + '" target="_blank" rel="noopener">' + _html(ev['name']) + '</a></td>'
        html += '<td>' + _html(when) + '</td>'
        html += '<td>' + str(_i(counts.get('leaders'))) + '</td>'
        html += '<td>' + str(_i(counts.get('members'))) + '</td>'
        html += '<td><a class="icon-btn" title="Involvement Dashboard" href="' + _html(dash) + '?org_id=' + str(ev['id'])
        html += '" target="_blank" rel="noopener"><i class="fa fa-bar-chart"></i></a></td></tr>'
    html += '</tbody></table></div></div></div>'

    drill = _s(_form_val('drill'))
    if drill == 'decisions':
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Decisions</h3>'
        html += _roster_table(decisions, 'Note date', can_write, 'SM Decisions', False, True)
        html += '</div>'
    elif drill == 'baptisms':
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Baptisms</h3>'
        html += _roster_table(baptisms, 'Baptism date', can_write, 'SM Baptisms', False, True)
        html += '</div>'
    elif drill == 'stories':
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Stories of Transformation</h3>'
        html += _roster_table(stories, 'Note date', can_write, 'SM Stories', False, True)
        html += '</div>'
    elif drill == 'attendance' or drill == 'meetings':
        att_key = _s(_form_val('att')) or 'week'
        spec = _att_drill_spec(cfg, att_key)
        title = spec[0] if spec else 'Attendance meetings'
        html += '<div class="vbs-card" id="sm-drill-list"><h3>' + _html(title) + '</h3>'
        html += _meetings_drill_html(cfg, att_key)
        html += '</div>'
    elif drill == 'fy_unique':
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Unique attends (ministry year)</h3>'
        html += _roster_table(
            _attend_people(_standing_orgs(cfg), fy_s, fy_e), '', can_write, 'SM FY Unique', False, False)
        html += '</div>'
    elif drill == 'enroll_unique':
        seen = {}
        uniq_people = []
        for p in enroll_people:
            pid = _i(p.get('people_id'))
            if pid not in seen:
                seen[pid] = True
                uniq_people.append(p)
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Unique event enrollments</h3>'
        html += _roster_table(uniq_people, 'Event', can_write, 'SM Event Unique', False, True)
        html += '</div>'
    elif drill == 'enroll_raw':
        html += '<div class="vbs-card" id="sm-drill-list"><h3>Raw event enrollments</h3>'
        html += _roster_table(enroll_people, 'Event', can_write, 'SM Event Raw', False, True)
        html += '</div>'
    return html


def _vol_list_hash(which):
    hashes = {
        'leaders': '#sm-vol-leaders',
        'coaches': '#sm-vol-coaches',
        'students': '#sm-vol-students',
        'campus': '#sm-vol-campus',
        'serving': '#sm-serving-beyond',
    }
    return hashes.get(_s(which), '')


def _vol_org_card(anchor, title, orgid, can_write, show_grade=False):
    html = '<div class="vbs-card" id="' + _html(anchor) + '"><h3>' + _html(title)
    if orgid > 0:
        html += ' <a href="/Org/' + str(orgid) + '" target="_blank" rel="noopener">#' + str(orgid) + '</a>'
    html += '</h3>'
    if orgid <= 0:
        html += '<div class="empty-state">Set this Involvement # on the Config tab.</div>'
    else:
        people = _org_members([orgid])
        html += _roster_table(
            people, '', can_write, 'SM ' + title, True, False, False, show_grade, show_grade)
    html += '</div>'
    return html


def _view_volunteers(cfg, can_write):
    serving = _serving_outside(cfg)
    html = '<div class="cover-head"><h2>Volunteers</h2>'
    html += '<p class="meta-line">Current members of the dedicated leader involvements. Onboarding stays in its own tool.</p></div>'
    html += '<div class="cover-cta">'
    html += '<a class="btn-primary" href="' + _html(_s(cfg.get('onboarding_url'))) + '" target="_blank" rel="noopener">Open Volunteer Onboarding</a>'
    html += '</div>'
    html += _demo_subnav(
        [
            ('sm-vol-leaders', 'Volunteer Leaders'),
            ('sm-vol-coaches', 'SG Coaches'),
            ('sm-vol-students', 'Student Lead Team'),
            ('sm-vol-campus', 'Campus Ministry'),
            ('sm-serving-beyond', 'Students Serving Beyond Refuge'),
        ],
        'Volunteers sections')
    html += _vol_org_card(
        'sm-vol-leaders', 'Volunteer Leaders', _cfg_i(cfg, 'leaders_orgid'), can_write, False)
    html += _vol_org_card(
        'sm-vol-coaches', 'SG Coaches', _cfg_i(cfg, 'coaches_orgid'), can_write, False)
    html += _vol_org_card(
        'sm-vol-students', 'Student Lead Team', _cfg_i(cfg, 'student_leaders_orgid'), can_write, True)
    html += '<div class="vbs-card" id="sm-vol-campus"><h3>Campus Ministry</h3>'
    html += '<div class="empty-state">Coming next.</div></div>'
    html += '<div class="vbs-card" id="sm-serving-beyond"><h3>Students Serving Beyond Refuge</h3>'
    html += '<p class="meta-line">Refuge standing members who are also in Volunteer Program '
    html += str(VOLUNTEER_PROGRAM_ID) + ' (or extra Org#s). Volunteer involvements are listed per student.</p>'
    html += _roster_table(serving, 'Volunteer involvements', can_write, 'SM Serving', True, True)
    html += '</div>'
    return html


def _view_demographics(cfg, can_write):
    people = _org_members(_standing_orgs(cfg), exclude_leaders=True)
    grade_f = _s(_form_val('grade'))
    gender_f = _s(_form_val('gender'))
    school_f = _s(_form_val('school'))
    q = _s(_form_val('q'))
    grades = {}
    schools = {}
    for p in people:
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
    html += '<p class="meta-line">Standing Middle School + High School members, excluding Leader member types. School District uses Extra Value School District.</p></div>'
    html += _demo_subnav()
    html += _grade_section(grades)
    html += _school_district_block(schools)
    bdays = _birthday_people(_standing_orgs(cfg))
    html += '<div class="vbs-card" id="sm-demo-birthdays"><h3>Birthdays this month</h3>'
    html += _roster_table(bdays, 'Birthday', can_write, 'SM Birthdays', False, True)
    html += '</div>'
    html += '<div class="vbs-card" id="sm-filtered-list"><h3>Master roster</h3>'
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
    kids_divs = []
    for k in ('kids_division_id', 'awana_division_id'):
        n = _cfg_i(cfg, k)
        if n > 0:
            kids_divs.append(n)
    kids_people = _people_on_divisions(kids_divs, _cfg_i(cfg, 'next_gen_program_id'))
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
    return html


def _person_in_group(person, group_name):
    g = ',' + _s(person.get('groups')).replace(', ', ',').lower() + ','
    return (',' + _s(group_name).lower() + ',') in g


def _sort_people(people):
    out = list(people or [])
    try:
        out.sort(key=lambda p: (
            _s(p.get('last')).lower(),
            _s(p.get('first')).lower(),
            _s(p.get('name')).lower(),
        ))
    except:
        pass
    return out


def _gender_counts(people):
    boys = 0
    girls = 0
    for p in people or []:
        g = _s(p.get('gender')).lower()
        if g.startswith('m'):
            boys += 1
        elif g.startswith('f'):
            girls += 1
    return boys, girls


def _group_member_table(people):
    people = _sort_people(people)
    html = '<div class="table-scroll"><table class="people-table sm-sortable"><thead><tr>'
    html += '<th class="sm-sort" data-sort="text">First</th>'
    html += '<th class="sm-sort" data-sort="text">Last</th>'
    html += '<th class="sm-sort" data-sort="text">Gender</th>'
    html += '<th class="sm-sort" data-sort="num">Age</th>'
    html += '<th class="sm-sort" data-sort="text">Grade</th>'
    html += '<th class="sm-sort" data-sort="text">School District</th>'
    html += '</tr></thead><tbody>'
    if not people:
        html += '<tr><td colspan="6"><div class="empty-state">No students</div></td></tr>'
    for p in people:
        first = _s(p.get('first')) or _s(p.get('name'))
        html += '<tr>'
        html += '<td>' + _person_link({'people_id': p.get('people_id'), 'name': first}) + '</td>'
        html += '<td>' + _html(p.get('last')) + '</td>'
        html += '<td>' + _html(p.get('gender')) + '</td>'
        html += '<td>' + _html(p.get('age')) + '</td>'
        html += '<td>' + _html(p.get('grade')) + '</td>'
        html += '<td>' + _html(p.get('school')) + '</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


def _sg_stat(n, label):
    return (
        '<div class="sg-stat"><div class="sg-stat-n">' + str(_i(n)) + '</div>'
        '<div class="sg-stat-l">' + _html(label) + '</div></div>'
    )


def _group_block_html(gname, leaders, students, can_write, idx=0, total=1):
    leaders = _sort_people(leaders)
    students = _sort_people(students)
    boys, girls = _gender_counts(students)
    team = len(leaders) + len(students)
    html = '<div class="sg-block demo-row is-collapsed">'
    html += '<div class="sg-block-header">'
    if can_write and total > 1:
        html += '<form method="post" action="' + _script_path() + '" class="sg-order">'
        html += '<input type="hidden" name="view" value="groups" />'
        html += '<input type="hidden" name="group_name" value="' + _html(gname) + '" />'
        up_dis = ' disabled' if idx <= 0 else ''
        down_dis = ' disabled' if idx >= total - 1 else ''
        html += '<button type="submit" name="action" value="sg_up" class="sg-order-btn"' + up_dis
        html += ' title="Move up" aria-label="Move ' + _html(gname) + ' up">'
        html += '<i class="fa fa-chevron-up" aria-hidden="true"></i></button>'
        html += '<button type="submit" name="action" value="sg_down" class="sg-order-btn"' + down_dis
        html += ' title="Move down" aria-label="Move ' + _html(gname) + ' down">'
        html += '<i class="fa fa-chevron-down" aria-hidden="true"></i></button>'
        html += '</form>'
    html += '<button type="button" class="demo-row-caret sg-caret" aria-expanded="false">'
    html += '<span class="sg-title">' + _html(gname) + '</span>'
    html += '<i class="fa fa-caret-down" aria-hidden="true"></i></button>'
    html += '<div class="sg-stats">'
    html += _sg_stat(team, 'Team')
    html += _sg_stat(len(students), 'Students')
    html += _sg_stat(boys, 'Boys')
    html += _sg_stat(girls, 'Girls')
    html += '</div>'
    html += _tag_add_button(leaders + students, 'SM ' + gname, can_write)
    html += '</div>'
    html += '<div class="sg-block-body demo-row-body">'
    html += '<div class="sg-leader-row"><span class="sg-leader-label">Leaders</span><span>'
    if leaders:
        bits = []
        for p in leaders:
            bits.append(_person_link(p, True))
        html += ', '.join(bits)
    else:
        html += '<em>No leaders assigned</em>'
    html += '</span></div>'
    html += _group_member_table(students)
    html += '</div></div>'
    return html


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
    html += _demo_subnav(
        [('sm-sg-groups', 'Groups'), ('sm-sg-assign', 'Assign')],
        'Small Groups sections')

    html += '<div id="sm-sg-groups" class="sg-stack">'
    if not names:
        html += '<div class="empty-state">No groups yet. Create one below.</div>'
    nlen = 0
    try:
        nlen = len(names)
    except:
        nlen = 0
    gi = 0
    for gname in names:
        g_leaders = []
        g_kids = []
        for p in leaders:
            if _person_in_group(p, gname):
                g_leaders.append(p)
        for p in students:
            if _person_in_group(p, gname):
                g_kids.append(p)
        html += _group_block_html(gname, g_leaders, g_kids, can_write, gi, nlen)
        gi += 1
    html += '</div>'

    html += '<div class="vbs-card" id="sm-sg-assign"><h3>Assign</h3>'
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
        html += '<button type="submit" name="action" value="sg_remove" class="btn-secondary">Remove from group</button>'
        html += '<label class="option-row"><input type="checkbox" name="add_only" value="1" checked /> Keep existing groups (add)</label>'
    html += '</div>'
    html += '<p class="meta-line">Select people below. Add keeps other groups. Move clears known group tags on that person, then assigns the new one. Remove drops the chosen group only.</p>'
    html += '<h4>Students</h4>'
    html += _roster_table(filtered, '', can_write, 'SM Assign', True, False, True)
    html += '<h4>Leaders (from dedicated involvements)</h4>'
    html += _roster_table(
        _org_members(_sg_assign_leader_orgs(cfg)), '', can_write, 'SM Leaders', True, False, True)
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
    html += _cfg_field(cfg, 'sunday_attendance_orgid', 'Sunday in-person attendance Org#', 'FCC default 35 — two Sunday meeting times, head count')
    html += _cfg_field(cfg, 'week_start_dow', 'Week start (0=Mon … 6=Sun)', 'Default 2 = Wednesday')
    html += _cfg_field(cfg, 'awag_division_ids', 'Average Week at a Glance Division Ids',
                    'Blank = divisions of the MS/HS orgs. Used for year-over-year (new involvements each year).')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Events (Prog/Div)</h3>'
    html += _cfg_field(cfg, 'event_program_id', 'Next Generation Program Id', 'FCC default 1112 — all Next Gen')
    html += _cfg_field(cfg, 'event_division_ids', 'Event Division Ids (comma-separated)', 'FCC default 46')
    html += _cfg_field(cfg, 'event_date_extra', 'Event date Extra Value name', 'Not used for When. When uses First/Last meeting dates on the involvement.')
    html += '</div>'
    html += '<div class="vbs-card"><h3>Leader involvements</h3>'
    html += _cfg_field(cfg, 'leaders_orgid', 'Volunteer Leaders Org#')
    html += _cfg_field(cfg, 'coaches_orgid', 'SG Coaches Org#')
    html += _cfg_field(cfg, 'student_leaders_orgid', 'Student Lead Team Org#')
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
    html += _cfg_field(cfg, 'next_gen_program_id', 'Next Generation Program Id', 'Always 1112 at FCC')
    html += _cfg_field(cfg, 'kids_division_id', 'Faith Kids Division Id')
    html += _cfg_field(cfg, 'awana_division_id', 'Awana Division Id')
    html += _cfg_field(cfg, 'senior_year_orgid', 'Senior Year Org# (0 = placeholder)')
    html += _cfg_field(cfg, 'volunteer_program_id', 'Volunteer Program Id (serving outside)', 'FCC default 1120')
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
    ny = BRAND['navy']
    wt = BRAND['white']
    gy = BRAND['gray']
    dg = BRAND['dark-gray']
    ar = BRAND['artisan']
    return (
        '.sm-root{display:block!important;visibility:visible!important;max-width:1400px;margin:0 auto;'
        'padding:20px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;'
        'background:' + wt + '!important;color:' + ny + '!important;min-height:240px}'
        '.dashboard-header{background:' + ny + ';color:' + wt + '!important;padding:18px 24px 16px;border-radius:12px;'
        'margin:0 auto 12px auto;box-shadow:0 4px 15px rgba(20,40,60,.25);text-align:center;max-width:960px}'
        '.sm-header-hero{text-align:center;margin:0 0 8px 0;line-height:0}'
        '.sm-header-hero img{display:block;margin:0 auto;max-height:110px;max-width:min(92%,720px);'
        'width:auto;height:auto;object-fit:contain}'
        '.dashboard-header h1{margin:0 0 4px;font-size:18px;font-weight:600;color:' + wt + '!important}'
        '.hdr-actions{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:8px;flex-wrap:wrap}'
        '.role-pill{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.35)}'
        '.btn-refresh{display:inline-block;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700;'
        'background:' + wt + ';color:' + ny + '!important;text-decoration:none!important;'
        'border:1px solid rgba(255,255,255,.55)}'
        '.btn-refresh:hover{background:' + gy + '}'
        '.dash-nav{text-align:center;margin:0 0 14px;background:' + wt + ';border:1px solid ' + gy + ';border-radius:10px;'
        'padding:8px 10px;box-shadow:0 1px 4px rgba(20,40,60,.06);position:relative}'
        '.dash-nav-caret{position:absolute;top:4px;right:6px;width:22px;height:22px;border:none;background:transparent;'
        'color:' + ny + ';cursor:pointer}'
        '.dash-nav.is-collapsed .dash-nav-body{display:none!important}'
        '.dash-nav-body,.dash-nav-segment,.dash-tabs{text-align:center;justify-content:center}'
        '.dash-nav-segment{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:4px 6px;margin:0 0 4px}'
        '.dash-tab{display:inline-block;border:1px solid ' + gy + ';background:' + wt + ';color:' + ny + '!important;padding:4px 10px;'
        'border-radius:6px;font-weight:600;font-size:12px;text-decoration:none!important;margin:1px 2px}'
        '.dash-tab:hover{border-color:' + ny + ';color:' + ny + '!important}'
        '.dash-tab.active{border-color:' + ny + ';background:' + ny + ';color:' + wt + '!important}'
        '.subtabs{margin:0 0 12px}'
        '.demo-subnav{text-align:center;position:sticky;top:0;z-index:6;background:' + wt + ';'
        'padding:8px 10px 10px;margin:0 0 14px;border:1px solid ' + ar + ';border-radius:10px}'
        '.demo-subnav .dash-tab{margin:3px;border-color:' + ar + '}'
        '.demo-subnav .dash-tab:hover{border-color:' + ny + ';color:' + ny + '!important}'
        '.demo-subnav .dash-tab.active{border-color:' + ny + ';background:' + ny + ';color:' + wt + '!important}'
        '.cover-head h2{margin:0 0 4px;color:' + ny + '}'
        '.cover-head-center,.cover-head-center h2,.cover-head-center .meta-line{text-align:center}'
        '.meta-line{color:' + ny + ';opacity:.7;font-size:13px;margin:4px 0 10px}'
        '.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin:0 0 16px}'
        '.stats-grid.compact{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}'
        '.home-row{margin:0 0 20px}'
        '.home-band{padding:16px 16px 10px;border-radius:12px;margin:0 0 14px}'
        '.home-band .home-row{margin:0 0 8px}'
        '.home-band .vbs-card{margin:0}'
        '.home-band-a{background:' + wt + '}'
        '.home-band-b{background:' + gy + '}'
        '.home-band-navy{background:' + ny + '}'
        '.home-band-navy .cover-head h2,.home-band-navy .home-row-title{color:' + wt + '}'
        '.home-band-navy .meta-line{color:' + wt + ';opacity:.85}'
        '.home-band-navy .stat-card,.home-band-navy a.stat-card{background:' + wt + '!important;color:' + ny + '!important}'
        '.home-band-navy .stat-value,.home-band-navy .stat-label{color:' + ny + '!important}'
        '.home-row-title{margin:0 0 8px;color:' + ny + ';font-size:16px}'
        '.home-row-title-artisan{color:' + ar + ';font-weight:700}'
        '.home-row-hero{grid-template-columns:1fr 1fr 1fr;gap:12px;margin:0 0 20px}'
        '.home-row-att{grid-template-columns:1fr 1fr 1fr 1fr;align-items:end}'
        '.home-row-att .stat-card{display:flex;flex-direction:column;justify-content:center;'
        'box-sizing:border-box;height:144px;min-height:144px;overflow:hidden}'
        '.home-row-fq{grid-template-columns:repeat(4,1fr);margin:12px 0 10px}'
        '.home-row-fq .stat-label{color:' + ar + ';margin-top:0;margin-bottom:6px}'
        '.home-row-level{grid-template-columns:1fr 1fr;margin:12px 0 10px;gap:16px}'
        '.home-level-col{display:flex;flex-direction:column;min-width:0}'
        '.home-row-level-months{grid-template-columns:1fr 1fr;margin:0;align-items:end}'
        '.home-month-col{display:flex;flex-direction:column;min-width:0}'
    '.home-month-title{margin:0 0 6px;color:' + dg + ';font-size:18px;font-weight:700}'
    '.home-level-title{margin:0 0 6px;color:' + ar + ';font-size:18px;font-weight:700}'
        '.home-row-events{grid-template-columns:repeat(4,1fr)}'
        '.demo-row{margin:0 0 16px;width:100%}'
        '.demo-row-caret{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;'
        'border:none;background:transparent;padding:0 0 8px;cursor:default;color:' + ny + ';text-align:left}'
        '.demo-row-title{margin:0;font-size:18px;font-weight:700;color:' + ny + '}'
        '.demo-row-caret i{display:none;color:' + ny + ';font-size:16px}'
        '.fq-block{margin:0 0 10px}'
        '.demo-row-caret.fq-caret{justify-content:center;cursor:pointer;padding:4px 0 8px}'
    '.fq-title{margin:0;font-size:16px;font-weight:700;color:' + ny + ';text-align:center}'
        '.demo-row-caret.fq-caret i{display:inline-block;color:' + ny + ';font-size:16px}'
        '.fq-block.is-collapsed .demo-row-body{display:none!important}'
        '.fq-block.is-collapsed .fq-caret i{transform:none}'
        '.fq-block:not(.is-collapsed) .fq-caret i{transform:rotate(180deg)}'
        '.demo-row-body{width:100%}'
        '.demo-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));width:100%;gap:10px;margin:0}'
        '.demo-grid .stat-card{text-align:center;min-width:0}'
        '.demo-grid .stat-label{color:' + ar + ';margin-top:0;margin-bottom:6px;word-break:break-word}'
        '.demo-grid .stat-value{color:' + ny + '}'
        '.demo-pie-wrap{display:flex;align-items:center;justify-content:center;gap:20px;flex-wrap:wrap;margin:14px 0 0}'
        '.demo-pie{width:220px;height:220px;max-width:100%}'
        '.demo-pie-legend{list-style:none;margin:0;padding:0;min-width:180px}'
        '.demo-pie-legend li{margin:0 0 6px}'
        '.demo-pie-legend a{display:flex;align-items:center;gap:8px;text-decoration:none!important;color:' + ny + '!important;font-size:12px}'
        '.demo-swatch{width:10px;height:10px;border-radius:2px;flex-shrink:0}'
        '.demo-pie-name{flex:1;font-weight:600}'
        '.demo-pie-n{opacity:.7;white-space:nowrap}'
        '.home-row-leaders{grid-template-columns:repeat(5,1fr)}'
        '#sm-drill-list{scroll-margin-top:16px}'
        '#sm-home-attendance,#sm-home-milestones,#sm-home-leaders,#sm-home-events,'
        '#sm-filtered-list,#sm-demo-grade,#sm-demo-schools,#sm-demo-birthdays,'
        '#sm-sg-groups,#sm-sg-assign,'
        '#sm-vol-leaders,#sm-vol-coaches,#sm-vol-students,#sm-vol-campus,'
        '#sm-serving-beyond{scroll-margin-top:52px}'
        '.stat-card{background:' + wt + ';border:1px solid #E2E5E8;border-radius:10px;padding:12px 14px;box-shadow:0 1px 4px rgba(20,40,60,.04);'
        'text-decoration:none!important;color:inherit!important;display:block}'
        '.stat-card.stat-hero{padding:28px 20px;text-align:center}'
        '.stat-card.stat-hero .stat-value{font-size:52px}'
        '.stat-card.stat-hero .stat-label{font-size:16px;margin-top:8px}'
        '.stat-card:hover{border-color:' + ar + ';box-shadow:0 0 0 3px ' + ar + '}'
        '.stat-value{font-size:28px;font-weight:700;color:' + ny + ';line-height:1.1}'
        '.stat-label{font-size:12px;font-weight:600;color:' + ny + ';margin-top:4px}'
        '.stat-sub{font-size:11px;color:' + ny + ';margin-top:4px}'
        '.delta-up{color:' + ny + ';font-weight:700}'
        '.delta-down{color:' + ar + ';font-weight:700}'
        '.delta-flat{color:' + ny + ';opacity:.7;font-weight:600}'
        '.unique-count{color:' + ar + ';font-weight:700;opacity:1}'
        '.vbs-card{background:' + wt + ';border:1px solid #E2E5E8;border-radius:12px;padding:16px;margin:0 0 16px;'
        'box-shadow:0 1px 4px rgba(20,40,60,.04)}'
        '.vbs-card h3{margin:0 0 8px;color:' + ny + ';font-size:18px}'
        '.people-table{width:100%;border-collapse:collapse;font-size:13px}'
        '.people-table th,.people-table td{padding:7px 8px;border-bottom:1px solid ' + gy + ';text-align:left}'
        '.people-table th{background:' + gy + ';color:' + ny + ';font-size:12px}'
        '.people-table .num{text-align:right}'
        '.sm-sort{cursor:pointer}'
        '.people-table a{color:' + ny + ';font-weight:600;text-decoration:none}'
        '.people-table a:hover{text-decoration:underline}'
        '.table-scroll{overflow-x:auto}'
        '.empty-state{padding:16px;color:' + ny + ';opacity:.65;text-align:center}'
        '.list-actions{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 8px;flex-wrap:wrap}'
        '.sm-root .btn-primary,.sm-root .btn-secondary,.sm-root .btn-tag-add,.sm-root .btn-tag-confirm{border:none;'
        'border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer;font-size:13px;'
        'text-decoration:none!important;display:inline-block}'
        '.sm-root .btn-primary,.sm-root .btn-tag-confirm{background:' + ny + ';color:' + wt + '!important}'
        '.sm-root .btn-secondary{background:' + wt + ';color:' + ny + '!important;border:1px solid #E2E5E8}'
        '.sm-root .btn-tag-add{background:' + gy + ';color:' + ny + '!important}'
        '.icon-btn{color:' + ny + ';font-size:16px;padding:4px}'
        'tr.event-upcoming td:first-child{border-left:3px solid ' + ny + '}'
        'tr.event-upcoming td:first-child a{color:' + ny + '}'
        'tr.event-past{color:' + ny + ';opacity:.5}'
        'tr.event-past a{color:' + ny + '!important}'
        '.info-banner{background:' + gy + ';border:1px solid #E2E5E8;color:' + ny + ';padding:10px 12px;border-radius:8px;margin:0 0 12px}'
        '.info-banner.danger{background:' + wt + ';border-color:' + ar + ';color:' + ar + '}'
        '.filter-bar,.assign-form .filter-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}'
        '.filter-bar input,.filter-bar select,.cfg-field input{padding:8px 10px;border:1px solid #E2E5E8;border-radius:8px;font-size:13px}'
        '.cfg-form .vbs-card{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}'
        '.cfg-form h3{grid-column:1/-1}'
        '.cfg-field{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:600;color:' + ny + '}'
        '.group-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin:0 0 16px}'
        '.group-card{background:' + wt + ';border:1px solid #E2E5E8;border-radius:10px;padding:12px}'
        '.group-card h3{margin:0 0 4px;color:' + ny + '}'
        '.sg-stack{display:flex;flex-direction:column;gap:12px;margin:0 0 16px}'
        '.sg-block{background:' + wt + ';border:1px solid #E2E5E8;border-radius:12px;padding:14px 16px;'
        'box-shadow:0 1px 4px rgba(20,40,60,.04)}'
        '.sg-block-header{display:flex;align-items:center;gap:12px;flex-wrap:wrap}'
        '.sg-order{display:flex;flex-direction:column;gap:2px;margin:0;flex:0 0 auto}'
        '.sg-order-btn{width:26px;height:20px;padding:0;border:1px solid #E2E5E8;background:' + wt + ';'
        'color:' + ny + ';border-radius:4px;cursor:pointer;line-height:1;font-size:10px}'
        '.sg-order-btn:hover{border-color:' + ny + '}'
        '.sg-order-btn:disabled{opacity:.35;cursor:default}'
        '.sg-caret{display:flex;align-items:center;gap:8px;border:none;background:transparent;padding:0;'
        'cursor:pointer;color:' + ny + ';text-align:left;flex:0 1 auto;width:auto}'
        '.sg-title{margin:0;font-size:18px;font-weight:700;color:' + ny + '}'
        '.sg-caret i{display:inline-block;color:' + ny + ';font-size:16px}'
        '.sg-block.is-collapsed .sg-caret i{transform:none}'
        '.sg-block:not(.is-collapsed) .sg-caret i{transform:rotate(180deg)}'
        '.sg-block.is-collapsed .sg-block-body{display:none!important}'
        '.sg-stats{display:grid;grid-template-columns:repeat(4,minmax(70px,1fr));gap:8px;flex:1;min-width:220px}'
        '.sg-stat{background:' + gy + ';border-radius:8px;text-align:center;padding:8px 6px}'
        '.sg-stat-n{font-size:20px;font-weight:700;color:' + ny + ';line-height:1.1}'
        '.sg-stat-l{font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:' + ny + ';opacity:.65;margin-top:2px}'
        '.sg-block-body{margin-top:12px}'
        '.sg-leader-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:' + gy + ';'
        'border-radius:8px;padding:8px 12px;margin:0 0 8px;border-left:3px solid ' + ny + '}'
        '.sg-leader-label{font-size:12px;font-weight:700;color:' + ny + ';min-width:64px}'
        '.sg-leader-row a{color:' + ny + ';font-weight:600;text-decoration:none}'
        '.sg-leader-row a:hover{text-decoration:underline}'
        '.sg-block .btn-tag-add{margin-left:auto}'
        '.cover-cta{margin:0 0 14px}'
        '.sm-root .tag-modal-overlay{display:none!important;position:fixed;inset:0;background:rgba(20,40,60,.45);'
        'z-index:40;align-items:center;justify-content:center}'
        '.sm-root .tag-modal-overlay.visible{display:flex!important}'
        '.tag-modal{background:#fff;border-radius:12px;max-width:420px;width:90%;padding:0;box-shadow:0 8px 30px rgba(20,40,60,.2)}'
        '.tag-modal-header{background:' + ny + ';color:#fff;padding:12px 16px;border-radius:12px 12px 0 0;font-weight:700}'
        '.tag-modal-body{padding:14px 16px}'
        '.tag-modal-body input[type=text],.tag-modal-body select{width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}'
        '.tag-source-panel{margin:0 0 10px 24px}'
        '.tag-modal-footer{padding:10px 16px 14px;display:flex;justify-content:flex-end;gap:8px}'
        '.option-row{display:flex;gap:8px;align-items:flex-start;font-size:12px;margin:8px 0;font-weight:500}'
        '@media (max-width:720px){'
        '.sm-root{padding:10px}'
        '.dashboard-header{padding:14px 12px 12px;max-width:100%}'
        '.sm-header-hero img{max-height:72px}'
        '.dashboard-header h1{font-size:15px}'
        '.dash-nav{text-align:center;padding:28px 8px 10px}'
        '.dash-nav-caret{left:50%;right:auto;transform:translateX(-50%);top:4px}'
        '.dash-nav-body,.dash-nav-segment,.dash-tabs{width:100%;text-align:center;justify-content:center}'
        '.dash-tab{margin:3px}'
        '.home-row-hero,.home-row-att,.home-row-events,.home-row-leaders,'
        '.home-row-fq,.home-row-level,'
        '.stats-grid,.stats-grid.compact,.demo-grid{grid-template-columns:1fr}'
        '.home-row-att .stat-card{height:auto;min-height:128px}'
        '.stat-card.stat-hero{padding:20px 12px}'
        '.stat-card.stat-hero .stat-value{font-size:40px}'
        '.demo-row-caret{cursor:pointer}'
        '.demo-row-caret i{display:inline-block}'
        '.demo-row.is-collapsed .demo-row-body{display:none!important}'
        '.demo-row.is-collapsed .demo-row-caret i{transform:rotate(180deg)}'
        '.fq-block.is-collapsed .fq-caret i{transform:none}'
        '.fq-block:not(.is-collapsed) .fq-caret i{transform:rotate(180deg)}'
        '.sg-block-header{flex-direction:column;align-items:stretch}'
        '.sg-stats{grid-template-columns:repeat(2,1fr);min-width:0}'
        '.sg-block .btn-tag-add{margin-left:0}'
        '.sg-block.is-collapsed .sg-caret i{transform:none}'
        '.sg-block:not(.is-collapsed) .sg-caret i{transform:rotate(180deg)}'
        '.group-grid{grid-template-columns:1fr}'
        '.cfg-form .vbs-card{grid-template-columns:1fr}'
        '.filter-bar,.assign-form .filter-bar,.list-actions{flex-direction:column;align-items:stretch}'
        '.filter-bar input,.filter-bar select,.cfg-field input{width:100%;box-sizing:border-box}'
        '.people-table{font-size:12px}'
        '.table-scroll{-webkit-overflow-scrolling:touch}'
        '}'
    )


def _page_script():
    path = _script_path()
    return (
        "(function(){try{"
        "var scriptUrl='" + path.replace("'", "\\'") + "';"
        "function $(s,r){return (r||document).querySelector(s);}"
        "function addClass(el,c){if(el) el.className=(el.className+' '+c).replace(/^\\s+|\\s+$/g,'');}"
        "function removeClass(el,c){if(!el)return;el.className=(' '+el.className+' ').replace(' '+c+' ',' ').replace(/^\\s+|\\s+$/g,'');}"
        "var pending=[];"
        "function parseIds(csv){var o=[],s={};String(csv||'').split(',').forEach(function(x){var n=parseInt(x,10);if(n>0&&!s[n]){s[n]=1;o.push(n);}});return o;}"
        "function tagSource(){var r=document.querySelector('input[name=tag-source]:checked');return r?r.value:'new';}"
        "function syncTagSource(){var src=tagSource();var ew=$('#tag-existing-wrap');var nw=$('#tag-new-wrap');"
        "if(ew)ew.style.display=src==='existing'?'block':'none';if(nw)nw.style.display=src==='new'?'block':'none';}"
        "function setTagSource(v){var radios=document.querySelectorAll('input[name=tag-source]');"
        "for(var i=0;i<radios.length;i++)radios[i].checked=(radios[i].value===v);syncTagSource();}"
        "function openTag(ids,sug){pending=ids||[];if(!pending.length){alert('No people in this list.');return;}"
        "var c=$('#tag-modal-count');if(c)c.textContent=pending.length+' people will be added.';"
        "var i=$('#tag-name-input');if(i)i.value=sug||'';"
        "var sel=$('#tag-existing-select');var matched=false;"
        "if(sel&&sug){var sl=String(sug).toLowerCase();for(var oi=0;oi<sel.options.length;oi++){"
        "if(String(sel.options[oi].value||'').toLowerCase()===sl){sel.selectedIndex=oi;matched=true;break;}}}"
        "if(sel&&!matched)sel.selectedIndex=0;"
        "if(matched)setTagSource('existing');else setTagSource('new');"
        "var o=$('#tag-modal-overlay');if(o)addClass(o,'visible');"
        "if(matched&&sel)try{sel.focus();}catch(e0){}else if(i)try{i.focus();}catch(e1){}}"
        "function closeTag(){var o=$('#tag-modal-overlay');if(o)removeClass(o,'visible');pending=[];}"
        "function submitTag(){var name='';"
        "if(tagSource()==='existing'){var sel=$('#tag-existing-select');name=sel?String(sel.value||'').replace(/^\\s+|\\s+$/g,''):'';"
        "if(!name){alert('Choose a tag.');return;}}"
        "else{var i=$('#tag-name-input');name=i?String(i.value||'').replace(/^\\s+|\\s+$/g,''):'';"
        "if(!name){alert('Enter a tag name.');return;}}"
        "if(!pending.length){alert('No people.');return;}"
        "var mode=$('input[name=tag-mode]:checked');var clear=mode&&mode.value==='clear';"
        "var openEl=$('#tag-open-when-done');var openDone=openEl?!!openEl.checked:true;"
        "var ids=pending.join(',');closeTag();"
        "var body='ajax=true&action=add_to_tag&people_ids='+encodeURIComponent(ids)+'&tag_name='+encodeURIComponent(name)+'&clear_first='+(clear?'1':'0');"
        "var x=new XMLHttpRequest();x.open('POST',scriptUrl,true);x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');"
        "x.onreadystatechange=function(){if(x.readyState!==4)return;var d=null;try{d=JSON.parse(x.responseText);}catch(e){alert('Tag failed.');return;}"
        "if(d&&d.error){alert(d.error);return;}if(openDone&&d&&d.tag_url)window.open(d.tag_url,'_blank','noopener');else alert((d&&d.count?d.count:0)+' added.');};"
        "x.send(body);}"
        "document.addEventListener('click',function(e){var t=e.target;"
        "var order=t;while(order&&order!==document){if(order.className&&(' '+order.className+' ').indexOf(' sg-order ')>=0)return;order=order.parentNode;}"
        "while(t&&t!==document){if(t.className&&(' '+t.className+' ').indexOf(' btn-tag-add ')>=0){e.preventDefault();openTag(parseIds(t.getAttribute('data-people-ids')),t.getAttribute('data-tag-suggest')||'');return;}"
        "if(t.id==='btn-tag-cancel'){e.preventDefault();closeTag();return;}"
        "if(t.id==='btn-tag-confirm'){e.preventDefault();submitTag();return;}"
        "if(t.id==='sm-nav-caret'){e.preventDefault();var n=document.getElementById('sm-dash-nav');if(n){if((' '+n.className+' ').indexOf(' is-collapsed ')>=0)removeClass(n,'is-collapsed');else addClass(n,'is-collapsed');}return;}"
        "if(t.className&&((' '+t.className+' ').indexOf(' demo-row-caret ')>=0||(' '+t.className+' ').indexOf(' sg-block-header ')>=0||(' '+t.className+' ').indexOf(' sg-stat ')>=0||(' '+t.className+' ').indexOf(' sg-title ')>=0)){e.preventDefault();var row=t;"
        "while(row&&row!==document){if(row.className&&(' '+row.className+' ').indexOf(' demo-row ')>=0){if((' '+row.className+' ').indexOf(' is-collapsed ')>=0)removeClass(row,'is-collapsed');else addClass(row,'is-collapsed');"
        "var exp=(' '+row.className+' ').indexOf(' is-collapsed ')<0;var caret=row.querySelector?row.querySelector('.demo-row-caret'):null;if(caret)caret.setAttribute('aria-expanded',exp?'true':'false');return;}row=row.parentNode;}return;}"
        "if(t.className&&(' '+t.className+' ').indexOf(' demo-jump ')>=0){e.preventDefault();"
        "var hid=String(t.getAttribute('href')||'').replace(/^#/,'');"
        "var el=document.getElementById(hid);if(el){var row=el;"
        "while(row&&row!==document){if(row.className&&(' '+row.className+' ').indexOf(' demo-row ')>=0){removeClass(row,'is-collapsed');break;}row=row.parentNode;}"
        "var nested=el.querySelectorAll?el.querySelectorAll('.demo-row'):[];"
        "if(hid==='sm-demo-grade'){for(var ni=0;ni<nested.length;ni++)removeClass(nested[ni],'is-collapsed');}"
        "var jumps=document.querySelectorAll('.demo-jump');for(var ji=0;ji<jumps.length;ji++){"
        "if((jumps[ji].getAttribute('href')||'').replace(/^#/,'')===hid)addClass(jumps[ji],'active');else removeClass(jumps[ji],'active');}"
        "jumpTo(hid);}return;}"
        "if(t.className&&(' '+t.className+' ').indexOf(' sm-sort ')>=0){e.preventDefault();sortTable(t);return;}"
        "t=t.parentNode;}});"
        "document.addEventListener('change',function(e){if(e.target&&e.target.name==='tag-source'){syncTagSource();return;}"
        "if(e.target&&e.target.className&&e.target.className.indexOf('sm-check-all')>=0){"
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
        "function jumpTo(id){if(!id)return;var el=document.getElementById(id);"
        "if(el)setTimeout(function(){try{el.scrollIntoView({behavior:'smooth',block:'start'});}catch(e3){el.scrollIntoView(true);}},80);}"
        "var sec='';var qs='';try{qs=window.location.search||'';var m=qs.match(/[?&]section=([^&]+)/);if(m)sec=decodeURIComponent(m[1]);}catch(e2){}"
        "if(!sec&&window.location.hash)sec=String(window.location.hash).replace(/^#/,'');"
        "if(sec==='serving')sec='sm-serving-beyond';"
        "if(!sec){try{if(/[?&]drill=/.test(qs))sec='sm-drill-list';"
        "else if(/[?&]view=volunteers/.test(qs)){var lm=qs.match(/[?&]list=([^&]+)/);var lk=lm?decodeURIComponent(lm[1]):'';"
        "if(lk==='coaches')sec='sm-vol-coaches';else if(lk==='students')sec='sm-vol-students';"
        "else if(lk==='campus')sec='sm-vol-campus';else if(lk==='serving')sec='sm-serving-beyond';"
        "else if(lk==='leaders')sec='sm-vol-leaders';}"
        "else if(/[?&](grade|gender|school|q)=/.test(qs)&&/[?&]view=demographics/.test(qs))sec='sm-filtered-list';}catch(e4){}}"
        "jumpTo(sec);"
        "}catch(err){}}"
        ")();"
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
    html += _tag_modal_html()
    html += '<div class="dashboard-header">'
    html += _header_hero_html(cfg)
    html += '<h1>' + _html(APP_TITLE) + '</h1>'
    html += '<div class="hdr-actions">'
    html += '<div class="role-pill">' + role_label + '</div>'
    html += _refresh_button(view)
    html += '</div></div>'
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
        elif action in ('sg_up', 'sg_down'):
            delta = -1
            if action == 'sg_down':
                delta = 1
            ok, message = _reorder_group(cfg, _form_val('group_name'), delta)
            view = 'groups'
        elif action in ('sg_add', 'sg_move', 'sg_remove'):
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
            if action == 'sg_remove':
                ok, message = _remove_many(cfg, ids, gname)
            else:
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
        '<div style="background:#FFFFFF;border:2px solid #DD5B58;color:#DD5B58;padding:16px;margin:12px;'
        'border-radius:8px;font-family:sans-serif"><strong>Student Ministry Central error</strong>'
        '<pre style="white-space:pre-wrap">' + _html(_ex_msg(ex)) + '\n' + _html(traceback.format_exc()) + '</pre></div>'
    )
    try:
        _show(err)
    except:
        print err
