import logging
import xml
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django_digest.decorators import httpdigest
from mangrove.transport import Request
from mangrove.transport.facade import TransportInfo
from mangrove.transport.player.player import XFormPlayer
from mangrove.transport.xforms.xform import list_all_forms, xform_for
from datawinners.accountmanagement.models import Organization
from datawinners.alldata.helper import get_all_project_for_user
from datawinners.main.utils import get_database_manager
from django.contrib.gis.utils import GeoIP
from datawinners.messageprovider.messages import SMART_PHONE

logger = logging.getLogger("datawinners.xform")
sp_submission_logger = logging.getLogger("sp-submission")

def restrict_request_country(f):
    def wrapper(*args, **kw):
        request = args[0]
        user = request.user
        org = Organization.objects.get(org_id=user.get_profile().org_id)
        try :
            country_code = GeoIP().country_code(request.META.get('REMOTE_ADDR'))
        except Exception as e:
            logger.exception("Error resolving country from IP : \n%s"%e)
            raise
        if country_code is None or org.country.code == country_code:
            return f(*args, **kw)
        return HttpResponse(status=401)

    return wrapper


@csrf_exempt
@httpdigest
@restrict_request_country
def formList(request):
    rows = get_all_project_for_user(request.user)
    form_tuples = [(row['value']['name'], row['value']['qid']) for row in rows]
    xform_base_url = request.build_absolute_uri('/xforms')
    response = HttpResponse(content=list_all_forms(form_tuples, xform_base_url), mimetype="text/xml")
    response['X-OpenRosa-Version'] = '1.0'
    return response


def get_errors(errors):
    return '\n'.join(['{0} : {1}'.format(key,val) for key, val in errors.items()])


def __authorized_to_make_submission_on_requested_form(request_user, submission_file):
    rows = get_all_project_for_user(request_user)
    questionnaire_ids = [(row['value']['qid']) for row in rows]
    dom = xml.dom.minidom.parseString(submission_file)
    requested_qid = dom.getElementsByTagName('data')[0].getAttribute('id')
    return requested_qid in questionnaire_ids


@csrf_exempt
@httpdigest
@restrict_request_country
def submission(request):
    if request.method != 'POST':
        response = HttpResponse(status=204)
        response['Location'] = request.build_absolute_uri()
        return response

    request_user = request.user
    submission_file = request.FILES.get("xml_submission_file").read()

    if not __authorized_to_make_submission_on_requested_form(request_user, submission_file) :
        response = HttpResponse(status=403)
        return response


    manager = get_database_manager(request_user)
    player = XFormPlayer(manager)
    try:
        mangrove_request = Request(message=submission_file,
            transportInfo=
            TransportInfo(transport=SMART_PHONE,
                source=request_user.email,
                destination=''
            ))

        response = player.accept(mangrove_request, logger=sp_submission_logger)

        if response.errors:
            logger.error("Error in submission : \n%s" % get_errors(response.errors))
            return HttpResponseBadRequest()

    except Exception as e:
        logger.exception("Exception in submission : \n%s" % e)
        return HttpResponseBadRequest()

    response = HttpResponse(status=201)
    response['Location'] = request.build_absolute_uri(request.path)
    return response


@csrf_exempt
@httpdigest
def xform(request, questionnaire_code=None):
    request_user = request.user
    form = xform_for(get_database_manager(request_user), questionnaire_code, request_user.get_profile().reporter_id)
    return HttpResponse(content= form, mimetype="text/xml")
