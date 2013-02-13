# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.template.defaultfilters import slugify
from fabric.colors import white
import xlwt
from datetime import datetime
from mangrove.datastore.database import get_db_manager
from django.utils.translation import ugettext_lazy as _
from datawinners import settings
from django.contrib.auth.forms import PasswordResetForm

VAR = "HNI"
def get_excel_sheet(raw_data, sheet_name):
    wb = xlwt.Workbook()
    workbook_add_sheet(wb, raw_data, sheet_name)
    return wb

def sorted_unique_list(value_list):
    return sorted(list(set(value_list)))

def get_database_manager_for_org(organization):
    from datawinners.accountmanagement.models import OrganizationSetting

    organization_settings = OrganizationSetting.objects.get(organization=organization)
    db = organization_settings.document_store
    return get_db_manager(server=settings.COUCH_DB_SERVER,database=db)

def get_organization(request):
    from datawinners.accountmanagement.models import Organization

    profile = request.user.get_profile()
    return Organization.objects.get(org_id=profile.org_id)

def get_organization_country(request):
    return get_organization(request).country_name()

def convert_to_ordinal(number):
    if 10 < number < 14: return _('%dth') % number
    if number % 10 == 1: return _('%dst') % number
    if number % 10 == 2: return _('%dnd') % number
    if number % 10 == 3: return _('%drd') % number
    return _('%dth') % number

def generate_document_store_name(organization_name,organization_id):
    return slugify("%s_%s_%s" % (VAR, organization_name, organization_id))

def get_organization_settings_from_request(request):
    from datawinners.accountmanagement.models import OrganizationSetting
    return OrganizationSetting.objects.get(organization = get_organization(request))

def _clean_date(date_val):
    new_date_val = date_val.replace(tzinfo=None)
    return new_date_val

def _clean(row):
    new_row = []
    for each in row:
        if type(each) is datetime:
            each = _clean_date(each)
        new_row.append(each)
    return new_row

def workbook_add_sheet_(wb, raw_data, sheet_name):
    ws = wb.add_sheet(sheet_name)
    default_cell_style=xlwt.Style.default_style
    dt_cell_style = xlwt.easyxf(num_format_str='dd-mm-yyyy hh:mm:ss')
    for row_number, row  in enumerate(raw_data):
        if row_number > 0 and row_number % 500 == 0: ws.flush_row_data()
        row = _clean(row)
        for col_number, val in enumerate(row):
            gangnam_style = dt_cell_style if isinstance(val, datetime) else default_cell_style;
            ws.write(row_number, col_number, val, style=gangnam_style)
    return ws

def workbook_add_sheet(wb, raw_data, sheet_name):
    ws = wb.add_sheet(sheet_name)
    default_cell_style=xlwt.Style.default_style
    dt_cell_style = xlwt.easyxf(num_format_str='dd-mm-yyyy hh:mm:ss')
    my_font = xlwt.Font()
    my_font.name = 'Times New Roman'
    my_font.bold = True
    my_font.colour_index = 0x33
    my_pattern = xlwt.Pattern()
    #https://secure.simplistix.co.uk/svn/xlwt/trunk/xlwt/Style.py for color codes
    my_pattern.pattern = 0x14
    header_style = xlwt.easyxf()
    header_style.font = my_font
    header_style.pattern = my_pattern
    for row_number, row  in enumerate(raw_data):

        if(row_number == 0):
            row = _clean(row)
            for col_number, val in enumerate(row):
                ws.col(col_number).width = 256 * (len(val) + 3)
                ws.write(row_number,col_number, val, header_style)

        if (row_number!=0):
            if row_number > 0 and row_number % 500 == 0: ws.flush_row_data()
            row = _clean(row)
            for col_number, val in enumerate(row):
#                ws.col(col_number).width = 256 * (len(val) + 1)
                gangnam_style = dt_cell_style if isinstance(val, datetime) else default_cell_style;
                ws.write(row_number, col_number, val, style=gangnam_style)
    return ws



def get_organization_from_manager(manager):
    from datawinners.accountmanagement.models import Organization, OrganizationSetting
    setting = OrganizationSetting.objects.get(document_store=manager.database_name)
    organization = Organization.objects.get(org_id=setting.organization_id)
    return organization

def send_reset_password_email(user, language_code):
    reset_form = PasswordResetForm({"email": user.email})
    if reset_form.is_valid():
        reset_form.save(email_template_name=_get_email_template_name_for_reset_password(language_code))

def _get_email_template_name_for_reset_password(language):
    return 'registration/password_reset_email_' + unicode(language) + '.html'

def convert_dmy_to_ymd(str_date):
    date = datetime.strptime(str_date, "%d-%m-%Y")
    return datetime.strftime(date, "%Y-%m-%d")

def get_changed_questions(olds, news, subject=True):
    i_old = 0
    deleted = []
    added = []
    changed = []
    changed_type = []
    if subject:
        if olds[-1].label != news[-1].label:
            changed.append(news[-1].label)
        olds = olds[:-1]
        news = news[:-1]
    for i_new, new in enumerate(news):
        while True:
            try:
                if new.name == olds[i_old].name:
                    if new.label!= olds[i_old].label:
                        changed.append(new.label)
                    elif new.type != olds[i_old].type:
                        changed_type.append(dict({"label": new.label, "type": new.type}))
                    i_old += 1
                    break
                deleted.append(olds[i_old].label)
                i_old += 1
            except IndexError:
                added.append(new.label)
                break

    if i_old < len(olds) :
        for key, old in enumerate(olds[i_old:]):
            deleted.append(old.label)

    all_type_dict = dict(changed=changed, changed_type=changed_type, added=added, deleted=deleted)
    return_dict = dict()
    for type, value in all_type_dict.items():
        if len(value):
            return_dict.update({type: value})
    return return_dict

def generate_project_name(project_names):
    default_name = _("Untitled Project")
    current_project = unicode(default_name)
    i = 1
    while current_project.lower() in project_names:
        current_project = u"%s - %d" % (default_name, i)
        i += 1
    return current_project

def _get_email_template_name_for_created_user(language):
    return 'registration/created_user_email_' + unicode(language) + '.html'