import elasticutils
from datawinners.main.database import get_database_manager
from datawinners.settings import ELASTIC_SEARCH_URL


class Query(object):
    def __init__(self, response_creator, query_builder,query_params):
        self.elastic_utils_helper = ElasticUtilsHelper()
        self.query_builder = query_builder
        self.response_creator = response_creator
        self.query_params = query_params

    def _getDatabaseName(self, user):
        return get_database_manager(user).database_name

    def get_headers(self, user, entity_type):
        pass


    def populate_query_options(self):
        options = {
            "start_result_number": self.query_params["start_result_number"],
            "number_of_results": self.query_params["number_of_results"],
            "order": self.query_params["order"],
        }
        return options

    def paginated_query(self, user, entity_type):
        entity_headers = self.get_headers(user, entity_type)
        options = self.populate_query_options()
        if self.query_params["order_by"] > 0:
            options.update({"order_field": entity_headers[self.query_params["order_by"]]})

        paginated_query = self.query_builder.create_paginated_query(entity_type, self._getDatabaseName(user), options)
        query_with_criteria = self.query_builder.add_query_criteria(entity_headers, self.query_params["search_text"],
                                                                    paginated_query)
        entities = self.response_creator.create_response(entity_headers, query_with_criteria)
        return query_with_criteria.count(), paginated_query.count(), entities


class QueryBuilder(object):
    def __init__(self):
        self.elastic_utils_helper = ElasticUtilsHelper()

    def create_query(self, doc_type, database_name):
        return elasticutils.S().es(urls=ELASTIC_SEARCH_URL).indexes(database_name).doctypes(doc_type).filter(void=False)

    def create_paginated_query(self, doc_type, database_name, query_params):
        start_result_number = query_params.get("start_result_number")
        number_of_results = query_params.get("number_of_results")
        order = query_params.get("order")
        order_by = query_params.get("order_field")
        query = self.create_query(doc_type, database_name)
        if order_by:
            query = query.order_by(order + order_by + "_value")
        return query[start_result_number:start_result_number + number_of_results]

    def add_query_criteria(self, query_fields, query_text, search):
        if query_text:
            query_text_escaped = self.elastic_utils_helper.replace_special_chars(query_text)
            raw_query = {
                "query_string": {
                    "fields": tuple(query_fields),
                    "query": query_text_escaped
                }
            }
            return search.query_raw(raw_query)

        return search.query()

class ElasticUtilsHelper():
    def replace_special_chars(self, search_text):
        lucene_special_chars = ['\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?',
                                '/',
                                ':']
        for char in lucene_special_chars:
            search_text = search_text.replace(char, '\\' + char)
        return search_text


