from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import sys
import os
# sys.path.append('../tariff-search') # IMPORTANT: required since we manually run this script from this location itself
sys.path.append(os.getcwd()) # IMPORTANT: required since we manually run this script from this location itself

commandLineArguments = sys.argv

for i in range(1,len(commandLineArguments),2):
    command = f"python initializers/create_vectorstore.py {commandLineArguments[i]} {commandLineArguments[i+1]}"
    os.system(command)
