import os
import json
from pathlib import Path

def loadJSONsAtRuntime() -> dict:
	print("Loading jsons into memory")

	filepath = 'functions\extract_data\extracted_data'
	json_dicts = {}

	for filename in os.listdir(filepath):
		f = os.path.join(filepath, filename)
		if os.path.isfile(f):
			print("Loading json @ " + f)
			json_dict = json.loads(Path(f).read_text())
			chapterNumber = json_dict["Chapter Number"]
			json_dicts[chapterNumber] = json_dict

	print("Loading jsons into memory completed.")
	return json_dicts