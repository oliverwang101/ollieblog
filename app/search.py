from flask import current_app
#functions check if app.elasticsearch == None, if so dont do anything
# model arguement is the SQLalchemy model, (the ones that add and remove entries)
def add_to_index(index, model):
    # can be used to add new or edited/existing entries to the index 
    if not current_app.elasticsearch:
        print("no elastic")
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, doc_type=index, id=model.id,
                                    body=payload)
def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)

def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index, doc_type=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
        # from = pagination math to calculate how many per page and  how many pages
    # list comprehension to extract id value from entire index
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    # return id of elements for search results
    # return total # of results, (search function helps with this)
    return ids, search['hits']['total']