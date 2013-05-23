import json
from main.utils import get_database_manager
from mangrove.datastore.database import get_db_manager
from project.models import get_all_projects

SEARCH_INDEX_DIRECTORY = "index"

DATABASE_NAME = "hni_testorg_slx364903"
SERVER = "http://admin:admin@localhost:5984/"
DATASENDER_VIEW = 'datasenders/datasenders'
PROJECT_VIEW = 'all_projects/all_projects'

import couchdb
from whoosh.index import create_in, os, exists_in, open_dir
from whoosh.fields import *


def get_datasender_project_association_dict(datasender):
    manager = get_db_manager(SERVER, DATABASE_NAME)
    #get_all_projects(manager, )


def index_doc(writer, doc, manager):
    name = doc['data']['name']['value']
    mobile_number = doc['data']['mobile_number']['value']
    location = ' '.join(doc['aggregation_paths']['_geo'])
    if doc['geometry']:
        gps = str(doc['geometry']['coordinates'][0]) + ',' + str(doc['geometry']['coordinates'][1])
    else:
        gps = ''
    email = ''
    short_code = doc["short_code"]
    rows = get_all_projects(manager, short_code)
    projects = [p.value["name"] for p in rows]
    devices_web = False
    writer.add_document(name=unicode(name), id=unicode(doc['_id']), mobile_number=unicode(mobile_number),
        location=unicode(location), gps=unicode(gps), email=unicode(email), short_code=unicode(short_code),
        projects=unicode(",".join(projects)), devices_web=devices_web)


def index_data_senders(writer, dbm):
    s = couchdb.Server(SERVER)
    d = s[DATABASE_NAME]

    data_senders = d.view(DATASENDER_VIEW, include_docs=True)

    for doc in data_senders:
        index_doc(writer, doc["doc"], dbm)

    writer.commit()


#cProfile.run("index_data_senders()")
def create_search_index(dbm):
    if not os.path.exists(SEARCH_INDEX_DIRECTORY):
        os.mkdir(SEARCH_INDEX_DIRECTORY)
    if not exists_in(SEARCH_INDEX_DIRECTORY):
        schema = Schema(id=ID(stored=True), name=TEXT(stored=True), mobile_number=TEXT(stored=True),
            short_code=TEXT(stored=True), location=TEXT(stored=True),
            gps=TEXT(stored=True), projects=TEXT(stored=True), email=TEXT(stored=True),
            devices_web=BOOLEAN(stored=True))
        ix = create_in(SEARCH_INDEX_DIRECTORY, schema)
        index_data_senders(ix.writer(), dbm)
        ix.close()


def search(param, pagenum=1, pagelen=10):
    from whoosh.qparser import MultifieldParser

    search_index = open_dir("index")
    with search_index.searcher() as searcher:
        query = MultifieldParser(["name", "mobile_number", "short_code", "location", "gps", "projects", "email"],
            search_index.schema).parse(unicode(param))

        results = searcher.search_page(query, pagenum, pagelen, terms=True)
        if len(results) > 0:
            print "length %s" % len(results)
            out = []
            for row in results:
                out.append(row.fields())
            return json.dumps(out)
        else: return json.dumps({'result': 'none found'})

