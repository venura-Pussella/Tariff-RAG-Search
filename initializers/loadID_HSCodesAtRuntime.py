import json
from pathlib import Path

def loadID_HSCodesAtRuntime() -> dict:
	"""Loads Azure Cosmos DB IDs to HSCode mapping from the path specified inside the function
	Returns:
		Returns the mapping as a dictionary.
	"""
	print("Loading ids and hscodes into memory")
	json_dicts = {}

	filepath = 'initializers/create_vectorstores/ids_hscode_dict.json'
	json_dicts = json.loads(Path(filepath).read_text())

	return json_dicts