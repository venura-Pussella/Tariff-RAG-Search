import os
import json
from pathlib import Path

def loadID_HSCodesAtRuntime() -> dict:
	print("Loading ids and hscodes into memory")

	filepath = 'initializers/create_vectorstores/ids_hscode_dict.json'
	json_dicts = json.loads(Path(filepath).read_text())

	return json_dicts