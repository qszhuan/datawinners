# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import logging

from django.contrib.auth.decorators import login_required as django_login_required, login_required
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User, Group
from django.core.mail import EmailMessage
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.contrib.auth.forms import PasswordResetForm
from datawinners.accountmanagement.post_activation_events import make_user_as_a_datasender
from datawinners.settings import HNI_SUPPORT_EMAIL_ID, EMAIL_HOST_USER, CRS_ORG_ID

from mangrove.errors.MangroveException import AccountExpiredException
from datawinners.accountmanagement.forms import OrganizationForm, UserProfileForm, EditUserProfileForm, UpgradeForm, ResetPasswordForm
from datawinners.accountmanagement.models import Organization, NGOUserProfile, PaymentDetails, MessageTracker, \
    DataSenderOnTrialAccount, get_ngo_admin_user_profiles_for, get_data_senders_on_trial_account_with_mobile_number
from django.contrib.auth.views import login, password_reset
from datawinners.main.utils import get_database_manager
from datawinners.project.models import get_all_projects
from django.utils.translation import ugettext as _, get_language, activate
from datawinners.project.models import Project
from datawinners.utils import get_organization, _get_email_template_name_for_reset_password, _get_email_template_name_for_created_user
from datawinners.activitylog.models import UserActivityLog
import json
from datawinners.common.constant import CHANGED_ACCOUNT_INFO, ADDED_USER, DELETED_USERS
from datawinners.entity.helper import send_email_to_data_sender, delete_datasender_for_trial_mode, \
    delete_datasender_from_project, delete_datasender_users_if_any, delete_entity_instance
from django.views.decorators.csrf import csrf_view_exempt, csrf_response_exempt
from mangrove.form_model.form_model import REPORTER
from mangrove.transport import Request, TransportInfo
from django.http import Http404

logger = logging.getLogger("django")
def is_admin(f):
    def wrapper(*args, **kw):
        user = args[0].user
        if not user.groups.filter(name="NGO Admins").count() > 0:
            return HttpResponseRedirect(django_settings.HOME_PAGE)

        return f(*args, **kw)

    return wrapper


def project_has_web_device(f):
    def wrapper(*args, **kw):
        request = args[0]
        user = request.user
        dbm = get_database_manager(user)
        project_id = kw["project_id"]
        project = Project.load(dbm.database, project_id)
        if "web" not in project.devices:
            referer = django_settings.HOME_PAGE
            return HttpResponseRedirect(referer)
        return f(*args, **kw)

    return wrapper


def is_datasender(f):
    def wrapper(*args, **kw):
        user = args[0].user
        if user.get_profile().reporter:
            return HttpResponseRedirect(django_settings.DATASENDER_DASHBOARD)

        return f(*args, **kw)

    return wrapper


def is_datasender_allowed(f):
    def wrapper(*args, **kw):
        user = args[0].user
        if user.get_profile().reporter:
            projects = get_all_projects(get_database_manager(user), user.get_profile().reporter_id)
        else:
            projects = get_all_projects(get_database_manager(user))
        project_ids = [project.id for project in projects]
        project_id = kw['project_id']
        if not project_id in project_ids:
            return HttpResponseRedirect(django_settings.DATASENDER_DASHBOARD)

        return f(*args, **kw)

    return wrapper


def is_new_user(f):
    def wrapper(*args, **kw):
        user = args[0].user
        if not len(get_all_projects(get_database_manager(args[0].user))) and not user.groups.filter(
            name="Data Senders").count() > 0:
            return HttpResponseRedirect("/start?page=" + args[0].path)

        return f(*args, **kw)

    return wrapper

def session_not_expired(f):
    def wrapper(*args, **kw):
        request = args[0]
        user = request.user
        try:
            user.get_profile()
        except NGOUserProfile.DoesNotExist:
            logger.exception("The session is expired")
            return HttpResponseRedirect(django_settings.INDEX_PAGE)
        except Exception as e:
            logger.exception("Caught exception when get user profile: " + e.message)
            return HttpResponseRedirect(django_settings.INDEX_PAGE)
        return f(*args, **kw)

    return wrapper


def is_not_expired(f):
    def wrapper(*args, **kw):
        request = args[0]
        user = request.user
        org = Organization.objects.get(org_id=user.get_profile().org_id)
        if org.is_expired():
            return HttpResponseRedirect(django_settings.TRIAL_EXPIRED_URL)
        return f(*args, **kw)

    return wrapper

def is_allowed_to_view_reports(f, redirect_to='/alldata'):
    def wrapper(*args, **kw):
        request = args[0]
        user = request.user
        profile = user.get_profile()
        if CRS_ORG_ID != profile.org_id and profile.reporter:
            return HttpResponseRedirect(redirect_to)
        return f(*args, **kw)

    return wrapper

def is_trial(f):
    def wrapper(*args, **kw):
        user = args[0].user
        profile = user.get_profile()
        organization = Organization.objects.get(org_id=profile.org_id)
        if not organization.in_trial_mode:
            return HttpResponseRedirect(django_settings.HOME_PAGE)
        return f(*args, **kw)

    return wrapper


def registration_complete(request):
    return render_to_response('registration/registration_complete.html')


def custom_login(request, template_name, authentication_form):
    if request.user.is_authenticated():
        return HttpResponseRedirect(django_settings.LOGIN_REDIRECT_URL)
    else:
        try:
            return login(request, template_name=template_name, authentication_form=authentication_form)
        except AccountExpiredException:
            return HttpResponseRedirect(django_settings.TRIAL_EXPIRED_URL)


def custom_reset_password(request):
    return password_reset(request,
        email_template_name=_get_email_template_name_for_reset_password(request.LANGUAGE_CODE),
        password_reset_form=ResetPasswordForm)


@login_required(login_url='/login')
@session_not_expired
@is_admin
@is_not_expired
def settings(request):
    if request.method == 'GET':
        organization = get_organization(request)
        organization_form = OrganizationForm(instance=organization)

        return render_to_response("accountmanagement/account/org_settings.html",
                {'organization_form': organization_form}, context_instance=RequestContext(request))

    if request.method == 'POST':
        organization = Organization.objects.get(org_id=request.POST["org_id"])
        organization_form = OrganizationForm(request.POST, instance=organization).update()
        if organization_form.errors:
            message = ""
        else:
            message = _('Settings have been updated successfully')
            changed_data = organization_form.changed_data
            if len(changed_data) != 0:
                detail_dict = dict()
                current_lang = get_language()
                activate("en")
                for changed in changed_data:
                    label = u"%s" % organization_form.fields[changed].label
                    detail_dict.update({label: organization_form.cleaned_data.get(changed)})
                activate(current_lang)
                detail_as_string = json.dumps(detail_dict)
                UserActivityLog().log(request, action=CHANGED_ACCOUNT_INFO, detail=detail_as_string)

        return render_to_response("accountmanagement/account/org_settings.html",
                {'organization_form': organization_form, 'message': message}, context_instance=RequestContext(request))


def _associate_user_with_existing_project(manager, reporter_id):
    rows = get_all_projects(manager)
    for row in rows:
        project_id = row['value']['_id']
        project = Project.load(manager.database, project_id)
        project.data_senders.append(reporter_id)
        project.save(manager)


@login_required(login_url='/login')
@session_not_expired
@is_admin
@is_not_expired
def new_user(request):
    add_user_success = False
    if request.method == 'GET':
        profile_form = UserProfileForm()
        return render_to_response("accountmanagement/account/add_user.html", {'profile_form': profile_form},
            context_instance=RequestContext(request))

    if request.method == 'POST':
        manager = get_database_manager(request.user)
        org = get_organization(request)
        form = UserProfileForm(organization=org, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            if not form.errors:
                user = User.objects.create_user(username, username, 'test123')
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                group = Group.objects.filter(name="Project Managers")
                user.groups.add(group[0])
                user.save()
                mobile_number = form.cleaned_data['mobile_phone']
                ngo_user_profile = NGOUserProfile(user=user, title=form.cleaned_data['title'],
                    mobile_phone=mobile_number,
                    org_id=org.org_id)
                ngo_user_profile.reporter_id = make_user_as_a_datasender(manager=manager, organization=org,
                    current_user_name=user.get_full_name(), mobile_number=mobile_number)
                ngo_user_profile.save()
                _associate_user_with_existing_project(manager, ngo_user_profile.reporter_id)
                reset_form = PasswordResetForm({"email": username})
                if reset_form.is_valid():
                    send_email_to_data_sender(reset_form.users_cache[0], request.LANGUAGE_CODE, request=request,
                                              type="created_user")
                    first_name = form.cleaned_data.get("first_name")
                    last_name = form.cleaned_data.get("last_name")
                    form = UserProfileForm()
                    add_user_success = True
                    detail_dict = dict({"First name": first_name, "Last name": last_name})
                    UserActivityLog().log(request, action=ADDED_USER, detail=json.dumps(detail_dict))

        return render_to_response("accountmanagement/account/add_user.html",
                {'profile_form': form, 'add_user_success': add_user_success},
            context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_admin
@is_not_expired
def users(request):
    if request.method == 'GET':
        org_id = request.user.get_profile().org_id
        not_datasenders = User.objects.exclude(groups__name='Data Senders').values_list('id', flat=True)
        users = NGOUserProfile.objects.filter(org_id=org_id, user__in=not_datasenders)
        return render_to_response("accountmanagement/account/users_list.html", {'users': users},
            context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def edit_user(request):
    if request.method == 'GET':
        profile = request.user.get_profile()
        if profile.mobile_phone == 'Not Assigned':
            profile.mobile_phone = ''
        form = EditUserProfileForm(data=dict(title=profile.title, first_name=profile.user.first_name,
            last_name=profile.user.last_name,
            username=profile.user.username,
            mobile_phone=profile.mobile_phone))
        return render_to_response("accountmanagement/profile/edit_profile.html", {'form': form},
            context_instance=RequestContext(request))
    if request.method == 'POST':
        form = EditUserProfileForm(request.POST)
        message = ""
        if form.is_valid():
            user = User.objects.get(username=request.user.username)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            ngo_user_profile = NGOUserProfile.objects.get(user=user)
            ngo_user_profile.title = form.cleaned_data['title']
            ngo_user_profile.mobile_phone = form.cleaned_data['mobile_phone']

            ngo_user_profile.save()
            message = _('Profile has been updated successfully')
        return render_to_response("accountmanagement/profile/edit_profile.html", {'form': form, 'message': message},
            context_instance=RequestContext(request))


def trial_expired(request):
    return render_to_response("registration/trial_account_expired_message.html")


@is_admin
@is_trial
def upgrade(request):
    profile = request.user.get_profile()
    organization = get_organization(request)
    if request.method == 'GET':
        form = UpgradeForm()
        return render_to_response("registration/upgrade.html", {'organization': organization, 'profile': profile,
                                                                'form': form}, context_instance=RequestContext(request))
    if request.method == 'POST':
        form = UpgradeForm(request.POST)
        if form.is_valid():
            organization.in_trial_mode = False
            organization.save()

            invoice_period = form.cleaned_data['invoice_period']
            preferred_payment = form.cleaned_data['preferred_payment']
            payment_details = PaymentDetails.objects.model(organization=organization, invoice_period=invoice_period,
                preferred_payment=preferred_payment)
            payment_details.save()
            message_tracker = MessageTracker.objects.filter(organization=organization)
            if message_tracker.count() > 0:
                tracker = message_tracker[0]
                tracker.reset()
            DataSenderOnTrialAccount.objects.filter(organization=organization).delete()
            _send_upgrade_email(request.user, request.LANGUAGE_CODE)
            messages.success(request, _("upgrade success message"))
            return HttpResponseRedirect(django_settings.LOGIN_REDIRECT_URL)

        return render_to_response("registration/upgrade.html", {'organization': organization, 'profile': profile,
                                                                'form': form}, context_instance=RequestContext(request))


def _send_upgrade_email(user, language):
    subject = render_to_string('accountmanagement/upgrade_email_subject_' + language + '.txt')
    subject = ''.join(subject.splitlines()) # Email subject *must not* contain newlines
    body = render_to_string('accountmanagement/upgrade_email_' + language + '.html', {'name': user.first_name})
    email = EmailMessage(subject, body, EMAIL_HOST_USER, [user.email], [HNI_SUPPORT_EMAIL_ID])
    email.content_subtype = "html"
    email.send()


def user_activity_log_details(users_to_be_deleted):
    return "<br><br>".join(("Name: " + user.get_full_name() + "<br>" + "Email: " + user.email) for user in users_to_be_deleted)

@login_required(login_url='/login')
@csrf_view_exempt
@csrf_response_exempt
@session_not_expired
@is_not_expired
def delete_users(request):
    if request.method == 'GET':
        raise Http404

    django_ids = request.POST.get("all_ids").split(";")
    all_ids = NGOUserProfile.objects.filter(user__in=django_ids).values_list('reporter_id', flat=True)
    manager = get_database_manager(request.user)
    organization = get_organization(request)
    transport_info = TransportInfo("web", request.user.username, "")
    ngo_admin_user_profile = get_ngo_admin_user_profiles_for(organization)[0]
    
    if ngo_admin_user_profile.reporter_id in all_ids:
        admin_full_name = ngo_admin_user_profile.user.first_name + ' ' + ngo_admin_user_profile.user.last_name
        messages.error(request, _("Your organization's account Administrator %s cannot be deleted") %
                                (admin_full_name), "error_message")
    else:
        detail = user_activity_log_details(User.objects.filter(id__in=django_ids))
        delete_entity_instance(manager, all_ids, REPORTER, transport_info)
        delete_datasender_from_project(manager, all_ids)
        delete_datasender_users_if_any(all_ids, organization)

        if organization.in_trial_mode:
            delete_datasender_for_trial_mode(manager, all_ids, REPORTER)
        action = DELETED_USERS
        UserActivityLog().log(request, action=action, detail=detail)
        messages.success(request, _("User(s) successfully deleted."))
        
    return HttpResponse(json.dumps({'success': True}))