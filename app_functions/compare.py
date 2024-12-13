import json

import config
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from app_functions import findByHSCode as fhs


def compare_releases(chapter_number: int, release1: str, release2: str) -> tuple[list,list,list,list]:
    """Does git-like version comparison between two documents that is the same chapter but of 2 releases.
    Git compares changes in lines. This compares changes in HS Codes.
    IMPORTANT: Assumes HS codes are sorted in the chapter-release JSON.

    Args:
        chapter_number (int): _description_
        release1 (str): old release
        release2 (str): new release

    Returns:
        tuple[list,list,list,list]: hscodes_with_no_change,hscodes_with_change,new_hscodes,removed_hscodes
    """

    # download jsons
    release1_json_bin = abo.download_blob_file_to_stream(f'{release1}/{chapter_number}.json', config.json_container_name)
    release2_json_bin = abo.download_blob_file_to_stream(f'{release2}/{chapter_number}.json', config.json_container_name)
    release1_json_bin.seek(0); release2_json_bin.seek(0)

    # convert to string
    release1_json_string = release1_json_bin.getvalue().decode('utf-8')
    release2_json_string = release2_json_bin.getvalue().decode('utf-8')

    # convert to lists of dictionary
    release1_dict = json.loads(release1_json_string)
    release2_dict = json.loads(release2_json_string)

    # get items of each release
    release1_item_list: list[dict] = release1_dict['Items']
    release2_item_list: list[dict] = release2_dict['Items']

    # get changes (similar to git version control comparison)
    return __compare_item_lists_twoPointerMethod(release1_item_list, release2_item_list)


def __compare_item_lists_twoPointerMethod(list1: list[dict], list2: list[dict]):

    hscodes_with_no_change = []
    hscodes_with_change = []
    new_hscodes = []
    removed_hscodes = []

    i = 0; j = 0
    while True:
        left = list1[i]
        right = list2[j]

        if left['HS Code'] == right['HS Code']: # can make comparison
            if __are_items_equal(left, right): 
                hscodes_with_no_change.append(left['HS Code'])
                print(f"Added {left['HS Code']} to no change.")
            else: 
                hscodes_with_change.append(left['HS Code'])
                print(f"Added {left['HS Code']} to changed.")
            i += 1; j += 1

        if left['HS Code'] > right['HS Code']:
            new_hscodes.append(right['HS Code'])
            print(f"Added {right['HS Code']} to new.")
            j += 1

        if left['HS Code'] < right['HS Code']:
            removed_hscodes.append(left['HS Code'])
            print(f"Added {left['HS Code']} to old.")
            i += 1


        if i >= len(list1):
            while j < len(list2):
                right = list2[j]
                new_hscodes.append(right['HS Code'])
                print(f"Added {right['HS Code']} to new.")
                j += 1
            break

        if j >= len(list2):
            while i < len(list1):
                left = list1[i]
                removed_hscodes.append(left['HS Code'])
                print(f"Added {left['HS Code']} to old.")
                i += 1
            break

    return hscodes_with_no_change,hscodes_with_change,new_hscodes,removed_hscodes


def __are_items_equal(item1: dict, item2: dict):
    for key in item1.keys():
        if item1[key] != item2[key]: return False
    return True

def get_lineitems_for_display_from_hscodes(hscodes: list[str], release: str):
    """Converts a list of hs codes into lineitems for displaying in the html dyanamic table.
    """
    results = []
    for hscode in hscodes:
        results += fhs.findByHSCode(hscode,[release])
    return results