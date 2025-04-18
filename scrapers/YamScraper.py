from Selectors import *
import os
from pathlib import Path
import yaml

class YamScraper:
    def __init__(self, yaml_str):
        # yaml_str might be a yaml string or a string location of a yaml file. Check if file exists first
        if os.path.exists(yaml_str):
            yaml_path = yaml_str
            try:
                with open(yaml_path, 'r') as file:
                    yaml_str = file.read()
            except Exception as e:
                print("There was an issue reading your yaml file: " + str(e))
                return None
        # either way, yaml should now contain the yaml text
        self.yam_dict = yaml.safe_load(yaml_str)

    # craft_selector iterates through the yaml and creates a Selector based on it
        
