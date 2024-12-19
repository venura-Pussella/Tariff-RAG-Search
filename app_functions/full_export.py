from data_stores.DataStores import DataStores

def get_all_lineitems() -> list[dict]:
    """Gets all lineitems in the json store"""

    lineitems = []

    chapter_dictionaries = DataStores.getJson_dicts()
    for chapterNumber_releaseDate_combo in chapter_dictionaries.keys():
        chapterNumber = chapterNumber_releaseDate_combo[0]
        releaseDate = chapterNumber_releaseDate_combo[1]
        chapter_dictionary = chapter_dictionaries[chapterNumber_releaseDate_combo]
        items = chapter_dictionary['Items']
        for item in items: 
            item['Release'] = releaseDate
            item['Chapter Number'] = chapterNumber
            lineitems.append(item)

    return lineitems