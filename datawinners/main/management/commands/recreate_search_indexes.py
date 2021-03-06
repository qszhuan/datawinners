import logging
from django.core.management.base import BaseCommand
import elasticutils
from datawinners.main.database import get_db_manager
from mangrove.datastore.documents import FormModelDocument
from datawinners.main.couchdb.utils import all_db_names
from datawinners.search import form_model_change_handler, entity_search_update
from datawinners.settings import ELASTIC_SEARCH_URL, ELASTIC_SEARCH_TIMEOUT
from mangrove.datastore.entity import Entity


def _create_mappings(dbm):
    for row in dbm.load_all_rows_in_view('questionnaire'):
        form_model_doc = FormModelDocument.wrap(row["value"])
        form_model_change_handler(form_model_doc, dbm)


def _populate_index(dbm):
    rows = dbm.database.iterview('by_short_codes/by_short_codes', 100, reduce=False, include_docs=True)
    for row in rows:
        entity = Entity.__document_class__.wrap(row.get('doc'))
        entity_search_update(entity, dbm)


def create_entity_index(dbname):
    dbm = get_db_manager(dbname)
    _create_mappings(dbm)
    _populate_index(dbm)


def recreate_index_for_db(database_name, es):
    try:
        es.delete_index(database_name)
    except Exception as e:
        logging.info("Could not delete index " + e.message)
    response = es.create_index(database_name, settings={"number_of_shards": 1, "number_of_replicas": 0})
    logging.info('%s search index created : %s' % (database_name, response.get('ok')))
    create_entity_index(database_name)

class Command(BaseCommand):
    def handle(self, *args, **options):
        es = elasticutils.get_es(urls=ELASTIC_SEARCH_URL, timeout=ELASTIC_SEARCH_TIMEOUT)
        if len(args) > 0:
            databases_to_index = args[0:]
        else:
            databases_to_index = all_db_names()
        for database_name in databases_to_index:
            recreate_index_for_db(database_name, es)
            print 'Done' + database_name

        print 'Completed!'
