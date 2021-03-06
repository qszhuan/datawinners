# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import datetime

from django.conf import settings
from django.contrib.auth import login
import elasticutils

from datawinners.accountmanagement.models import Organization, OrganizationSetting, DataSenderOnTrialAccount
from datawinners.feeds.database import get_feed_db_from_main_db_name
from datawinners.main.management.sync_changed_views import SyncOnlyChangedViews
from datawinners.settings import ELASTIC_SEARCH_URL
from mangrove.errors.MangroveException import DataObjectAlreadyExists
from mangrove.transport.repository.reporters import REPORTER_ENTITY_TYPE
from mangrove.datastore.entity import create_entity
from mangrove.datastore.datadict import get_or_create_data_dict
from mangrove.form_model.form_model import REPORTER, MOBILE_NUMBER_FIELD, NAME_FIELD, EMAIL_FIELD
from mangrove.datastore.queries import get_entity_count_for_type


def create_feed_database(db_name):
    feed_manager = get_feed_db_from_main_db_name(db_name)
    assert feed_manager, "Could not create feed database manager for %s " % (db_name,)
    SyncOnlyChangedViews().sync_feed_views(feed_manager)
    return feed_manager


def create_org_database(db_name):
    from datawinners.initializer import run
    from datawinners.main.database import get_db_manager

    manager = get_db_manager(db_name)
    assert manager, "Could not create database manager for %s " % (db_name,)
    create_search_index(db_name)
    run(manager)
    return manager


def initialize_organization(sender, user, request, **kwargs):
    profile = user.get_profile()
    org = Organization.objects.get(org_id=profile.org_id)
    active_organization(org)

    org_settings = OrganizationSetting.objects.get(organization=org)
    db_name = org_settings.document_store
    #    Explicitly create the new database. Should fail it db already exists.
    manager = create_org_database(db_name)
    if settings.FEEDS_ENABLED:
        create_feed_database(db_name)
    profile.reporter_id = make_user_as_a_datasender(manager, org, user.get_full_name(), profile.mobile_phone,
                                                    profile.user.email)
    profile.save()
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)


def create_search_index(db_name):
    es = elasticutils.get_es(urls=ELASTIC_SEARCH_URL)
    index_settings = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            }}}
    es.create_index(db_name, index_settings)


def active_organization(org):
    if org is None:
        return None

    active_date = org.active_date

    if active_date is None:
        now = datetime.datetime.now().replace(microsecond=0)
        org.active_date = now
        org.status_changed_datetime = now
        org.status = 'Activated'
        org.save()


def make_user_as_a_datasender(manager, organization, current_user_name, mobile_number, email=None):
    total_entity = get_entity_count_for_type(manager, [REPORTER])
    reporter_id = None
    offset = 1
    while not reporter_id:
        reporter_short_code = 'rep' + str(total_entity + offset)
        try:
            entity = create_entity(dbm=manager, entity_type=REPORTER_ENTITY_TYPE, short_code=reporter_short_code,
                                   location=[organization.country_name()])
            reporter_id = entity.short_code
        except DataObjectAlreadyExists as ignore:
            offset += 1

    mobile_number_type = get_or_create_data_dict(manager, name='Mobile Number Type', slug='mobile_number',
                                                 primitive_type='string')
    name_type = get_or_create_data_dict(manager, name='Name', slug='name', primitive_type='string')
    data = [(MOBILE_NUMBER_FIELD, mobile_number, mobile_number_type), (NAME_FIELD, current_user_name, name_type)]
    if email:
        data.append((EMAIL_FIELD, email, name_type ))
    entity.add_data(data=data)
    entity.save()

    if organization.in_trial_mode:
        data_sender = DataSenderOnTrialAccount.objects.model(mobile_number=mobile_number,
                                                             organization=organization)
        data_sender.save()
    return entity.short_code


