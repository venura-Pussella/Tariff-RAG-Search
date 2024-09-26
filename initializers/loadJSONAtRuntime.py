def loadJSONsAtRuntime() -> dict:
	"""Loads the .json files (the extracted data from the PDFs) into memory from the filepath defined in the function, and returns them as a dictionary.
	"""
	import os
	import json
	from pathlib import Path

	print("Loading jsons into memory")

	filepath = 'initializers/extract_data/extracted_data'
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