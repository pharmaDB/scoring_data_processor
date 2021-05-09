import json
from orangebook.merge import OrangeBookMap
from utils import misc


def export_all_NDA(file_name):
    """Exports list of all NDA from the Orange Book to a file"""
    ob = OrangeBookMap()
    all_NDA_in_Orange_Book = ob.get_all_nda()
    misc.store_to_file(file_name, all_NDA_in_Orange_Book)


def export_all_patents(file_name, json_convert=False):
    """
    Exports list of all patents from the Orange Book to a file. If
    json_convert is True, the export is formatted as json.
    """
    ob = OrangeBookMap()
    all_patents_in_Orange_Book = ob.get_all_patents()
    if not json_convert:
        misc.store_to_file(file_name, all_patents_in_Orange_Book)
    else:
        misc.store_to_file(file_name, json.dumps(all_patents_in_Orange_Book))


def export_missing_NDA(mongo_client, file_name):
    """
    Exports list of missing NDA from the database to a file.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        file_name (Path):  location to export list of missing NDAs
    """
    label_collection = mongo_client.label_collection
    ob = OrangeBookMap()
    all_NDA_in_Orange_Book = ob.get_all_nda()
    all_NDA_in_MongoDB = label_collection.distinct("application_numbers")
    all_NDA_in_MongoDB = [int(x) for x in all_NDA_in_MongoDB]
    NDA_in_OB_not_in_Mongo = [
        x for x in all_NDA_in_Orange_Book if x not in all_NDA_in_MongoDB
    ]
    misc.store_to_file(file_name, NDA_in_OB_not_in_Mongo)


def export_missing_patents(mongo_client, file_name, json_convert=False):
    """
    Exports list of missing patents from the database to a file. If
    json_convert is True, the export is formatted as json.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        file_name (Path):  location to store export list of missing patents
        json_convert (Boolean): whether the output should be in json format
    """
    patent_collection = mongo_client.patent_collection
    ob = OrangeBookMap()
    all_patents_in_Orange_Book = ob.get_all_patents()
    print(all_patents_in_Orange_Book[:10])
    all_patents_in_MongoDB = patent_collection.distinct("patent_number")
    print(all_patents_in_MongoDB[:10])
    patents_in_OB_not_in_Mongo = [
        x for x in all_patents_in_Orange_Book if x not in all_patents_in_MongoDB
    ]
    print(patents_in_OB_not_in_Mongo[:10])
    if not json_convert:
        misc.store_to_file(file_name, patents_in_OB_not_in_Mongo)
    else:
        misc.store_to_file(file_name, json.dumps(patents_in_OB_not_in_Mongo))

