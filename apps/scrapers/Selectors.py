#!/usr/bin/env python3
# sample_scrape.py

import requests
from bs4 import BeautifulSoup
import bs4
from enum import Enum
import copy
from abc import ABC
from copy import deepcopy
import re
import yaml

# Selecteds are the return values of Selectors. They can be Multiples (lists of Selecteds), Singles (pieces of the DOM tree), or Values (terminal values that will not have any further selection performed on them)
class SelectedType(Enum):
    VALUE = 0
    SINGLE = 1
    MULTIPLE = 2

class Selected:
    def __init__(self, value, selected_type):
        self.value = value
        self.selected_type = selected_type
        potential_type_error = self.__validate_selected_type()

        if potential_type_error != None:
            raise potential_type_error


    @property
    def collapsed_value(self):
        if self.selected_type == SelectedType.MULTIPLE:
            return [sub_selected.collapsed_value for sub_selected in self.value]
        else:
            return self.value



    def __str__(self):
        if self.selected_type != SelectedType.MULTIPLE:
            return str(self.value)
        else:
            return str(self.values())

    def values(self):
        return [el.value for el in self.value]


    def __validate_selected_type(self):
        sts = SelectedType.VALUE
        sts = SelectedType.SINGLE
        stm = SelectedType.MULTIPLE
       # verify that the element being saved in self is of an appropriate type
        selected_type_to_allowed_types = {
            sts: [bs4.element.Tag, BeautifulSoup],
            stm: [list]
        }
        if self.selected_type in selected_type_to_allowed_types:
            allowed_types = selected_type_to_allowed_types[self.selected_type]
            if type(self.value) not in allowed_types:
                return TypeError("Selected of type " + self.selected_type.name + " must have a value of type " + " or ".join([str(typ) for typ in allowed_types])+ ". Your value is of type " + str(type(self.value)))

        # additional check for multiple that its children are all other selecteds
        if self.selected_type == SelectedType.MULTIPLE:
            if not all([isinstance(el, Selected) for el in self.value]):
                return TypeError("Selecteds of type Multiple must be lists of other Selecteds")

        return None


class Selector(ABC):
    def validate_selected_type(self, selected):
        if isinstance(self.expected_selected, list):
            if selected.selected_type not in self.expected_selected:
                raise TypeError(str(type(self)) + " expects a Selected of type " + " or ".join([expsel.name for exspel in self.expected_selected]) + ", but received " + selected.selected_type.name)
        else:
            if selected.selected_type != self.expected_selected:
                raise TypeError(str(type(self)) + " expects a Selected of type " + self.expected_selected.name + ", but received " + selected.selected_type.name)

    def __call__(self, selected):
        return self.select(selected)

    def select(self, selected):
        self.validate_selected_type(selected)

    def fromYamlDict(yamlDict):
        # Determine what the top level is. if it's a list it must be a seriessel
        if isinstance(yamlDict, list):
            return SeriesSelector.fromYamlDict(yamlDict)
        elif isinstance(yamlDict, str):
            string_specs_dict = {
                "text_selector": TextSelector,
                "html_selector": HtmlSelector
            }
            if yamlDict in string_specs_dict:
                return string_specs_dict[yamlDict].fromYamlDict(yamlDict)
        elif isinstance(yamlDict, dict):
            dict_specs_dict = {
                "soup_selector": SoupSelector,
                "indexed_selector": IndexedSelector,
                "attr_selector": AttrSelector,
                "for_each_selector": ForEachSelector,
                "mapping_selector": MappingSelector,
                "split_selector": SplitSelector,
                "file_selector": FileSelector,
                "print_selector": PrintSelector,
                "concat_selector": ConcatSelector,
                "plain_text_selector": PlainTextSelector,
                "css_selector": CSSSelector,
                'zip_selector': ZipSelector
            }
            # there will only be one key in the dict, and it'll be the name of the selector
            for key, value in yamlDict.items():
                sole_selector = key
                sole_arguments = value

            try:
                return dict_specs_dict[sole_selector].fromYamlDict(sole_arguments)
            except Exception as e:
                print(sole_selector, "<- selector\n", sole_arguments, "<- arguments")
                raise Exception("errored: " + str(e))

    def fromFilePath(file_path):
        try:
            with open(file_path, 'r') as file:
                yaml_file = file.read()

            yaml_dict = yaml.safe_load(yaml_file)
            if yaml_dict == None:
                raise Exception("No contents of file!")

        except Exception as e:
            print("There was an issue trying to load the file! Error:\n", e)
            return None

        return Selector.fromYamlDict(yaml_dict)


    def toYamlDict(self):
        pass

class PlainTextSelector(Selector):
    def __init__(self, text):
        self.text = text

    def select(self, selected):
        return Selected(self.text, SelectedType.VALUE)

    def toYamlDict(self):
        return {"plain_text_selector": {"text": self.text}}

    def fromYamlDict(yamlDict):
        print("Text is " + yamlDict["text"])
        return PlainTextSelector(yamlDict["text"])


class CSSSelector(Selector):
    def __init__(self, css_selector, index=None):
        self.expected_selected = SelectedType.SINGLE
        self.css_selector_text = css_selector
        self.index = index

    def select(self, selected):
        super().select(selected)
        selecteds = Selected([Selected(sub_selected, SelectedType.SINGLE) for sub_selected in selected.value.select(self.css_selector_text)], SelectedType.MULTIPLE)
        if self.index != None:
            return IndexedSelector(self.index).select(selecteds)
        else:
            return selecteds

    def toYamlDict(self):
        return {"css_selector": {"css_selector": self.css_selector_text}}

    def fromYamlDict(yamlDict):
        if "index" in yamlDict:
            return CSSSelector(yamlDict["css_selector"], index=yamlDict["index"])
        else:
            return CSSSelector(yamlDict["css_selector"] )

# A TextSelector takes a Selected Single and returns the text value within it.
# S->V
class TextSelector(Selector):
    def __init__(self):
        self.expected_selected = SelectedType.SINGLE

    def select(self, selected):
        super().select(selected)
        return Selected(str(selected.value.get_text()).strip(), SelectedType.VALUE)

    def toYamlDict(self):
        return 'text_selector'

    def fromYamlDict(yamlDict):
        return TextSelector()

# An HTMLSelector takes a Selected Single and returns the whole html value within it.
# S->V
class HtmlSelector(Selector):
    def __init__(self):
        self.expected_selected = SelectedType.SINGLE

    def select(self, selected):
        super().select(selected)

        return Selected(str(selected.value.prettify()).strip(), SelectedType.VALUE)

    def toYamlDict(self):
        return 'html_selector'

    def fromYamlDict(yamlDict):
        return HtmlSelector()

# Creates a selector based on a secondary file. Allows for neatening of files
class FileSelector(Selector):
    def __init__(self, file_path):
        self.file_path = file_path

        self.selector = Selector.fromFilePath(file_path)

    def select(self, selected):
        
        return self.selector.select(selected)

    def toYamlDict(self):
        return self.selector.toYamlDict()

    def fromYamlDict(yamlDict):
        return FileSelector(yamlDict['file_path'])

class ConcatSelector(Selector):
    def __init__(self, first, second):
        self.first = first
        self.second = second
        print("concat inited")

    def select(self, selected):
        return Selected(str(self.first.select(selected).collapsed_value) + str(self.second.select(selected).collapsed_value), SelectedType.VALUE)

    def toYamlDict(self):
        return {"concat_selector": {first: self.first.toYamlDict(), second: self.second.toYamlDict()}}

    def fromYamlDict(yamlDict):
        print("About to init concat")
        return ConcatSelector(Selector.fromYamlDict(yamlDict['first']), Selector.fromYamlDict( yamlDict['second'] ))


# A SoupSelector is initialized with a dictionary of attribute names to values. It takes a Selected Single and finds all children of the Single that have those values for those attributes. Use tag_name to target a tag. Has an optional "index" parameter that can be used to specify an index, which will be accessed using an IndexedSelector
# S->M
class SoupSelector(Selector):
    def __init__(self, attrs, re_attrs=None, index=None):
        self.original_attrs = attrs
        self.original_re_attrs = re_attrs
        new_attrs = deepcopy(attrs)

        # compile any regex type attributes
        if re_attrs != None:

            for key, val in re_attrs.items():
                compiled = re.compile(val)
                new_attrs[key] = re.compile(val)


        self.expected_selected = SelectedType.SINGLE
        self.tagname = new_attrs.pop("tag_name") if "tag_name" in attrs else None
        self.attrs = new_attrs
        self.index=index

    def select(self, selected):
        super().select(selected)

        if self.tagname != None:
            values = selected.value.find_all(self.tagname, attrs=self.attrs)
        else:
            values = selected.value.find_all(attrs=self.attrs)

        selecteds = Selected([Selected(val, SelectedType.SINGLE) for val in values], SelectedType.MULTIPLE)
        if self.index != None:
            return IndexedSelector(self.index).select(selecteds)
        return selecteds

    def toYamlDict(self):
        args_dict = {}
        args_dict['attrs'] = self.original_attrs

        if self.index != None:
            args_dict['index'] = self.index

        if self.original_re_attrs != None:
            args_dict['re_attrs'] = self.original_re_attrs

        return {'soup_selector': args_dict}

    def fromYamlDict(yamlDict):
        if 'index' in yamlDict:
            return SoupSelector(yamlDict['attrs'], index=yamlDict['index'])

        attrs_dict = deepcopy(yamlDict['attrs'])

        re_attrs_dict = deepcopy(yamlDict['re-attrs']) if 're-attrs' in yamlDict else None


        return SoupSelector(yamlDict['attrs'], re_attrs_dict)




# An IndexedSelector is initialized with an index n. It takes a Selected Multiple and returns the nth element of it.
# M->S
class IndexedSelector(Selector):
    def __init__(self, index):
        self.expected_selected = SelectedType.MULTIPLE
        self.index = index

    def select(self, selected):
        super().select(selected)

        return selected.value[self.index]

    def toYamlDict(self):
        return {'indexed_selector': {'index': self.index}}

    def fromYamlDict(yamlDict):
        return IndexedSelector(yamlDict['index'])



# An AttrSelector selects a given attribute from a Selected Single
# S->V
class AttrSelector(Selector):
    def __init__(self, attr):
        self.expected_selected = SelectedType.SINGLE
        self.attr = attr

    def select(self, selected):
        super().select(selected)
        return Selected(selected.value[self.attr], SelectedType.VALUE)

    def toYamlDict(self):
        return {'attr_selector': {'attr': self.attr}}

    def fromYamlDict(yamlDict):
        return AttrSelector(yamlDict['attr'])

# Split Selector takes a Selected Single (which it will turn to HTML) or a Selected Value. It splits that string by the string delimiter, and returns a Selected Multiple of Selected Values.
class SplitSelector(Selector):
    def __init__(self, delimiter):
        self.expected_selected = [SelectedType.VALUE, SelectedType.SINGLE]
        self.delimiter = delimiter

    def select(self, selected):
        text_rep = str(selected.value if selected.selected_type == SelectedType.SINGLE else selected.value)
        split_up = text_rep.split(self.delimiter)
        portions = []

        for portion in split_up:
            portion_soup = BeautifulSoup(portion, 'html.parser')
            portion_single = Selected(portion_soup, SelectedType.SINGLE)
            portions.append(portion_single)


        return Selected(portions, SelectedType.MULTIPLE)

    def fromYamlDict(yamlDict):
        return SplitSelector(yamlDict['delimiter'])

    def toYamlDict(self):
        return {"split_selector": {"delimiter": self.delimiter}}


# A SeriesSelector is initialized with a list of Selectors. It takes a Selected of the type expected by its first selector and calls the selectors in sequence, returning the final value.
# Variable type, depends on selectors assigned to it
class SeriesSelector(Selector):
    def __init__(self, selectors):
        self.selectors = selectors

    def select(self, selected):

        current = selected
        series_copy = deepcopy(self.selectors)
        while series_copy != []:
            current = series_copy.pop(0).select(current)

        return current

    def toYamlDict(self):
        return [selector.toYamlDict() for selector in self.selectors]

    def fromYamlDict(yamlDictList):
        subSelectors = [Selector.fromYamlDict(subYamlDict) for subYamlDict in yamlDictList]
        return SeriesSelector(subSelectors)

class PrintSelector(Selector):
    def __init__(self, message, print_selected=False):
        self.message = message
        self.print_selected = print_selected

    def select(self, selected):
        print(self.message)
        if self.print_selected:
            print("PrintSelector report.\nSelected Type:", selected.selected_type, "\nCollapsed Value:", selected.collapsed_value)
        return selected

    def toYamlDict(self):
        if print_selected:
            return {"print_selector": {"message": self.message, "print_selected": True}}
        return {"print_selector": {"message": self.message}}

    def fromYamlDict(yamlDict):
        return PrintSelector(yamlDict["message"], print_selected=("print_selected" in yamlDict and yamlDict["print_selected"]))

# A ForEachSelector is initialized with a Selector of any type (including a SeriesSelector). It takes a Selected Multiple and returns a Selected Multiple, where each Selected in the returned Selected Multiple is the result of applying the selector to an element of the inputted Selected Multiple (in order)
# M->M
class ForEachSelector(Selector):
    def __init__(self, selector, skip_on_fail=False):
        self.expected_selected = SelectedType.MULTIPLE
        self.selector = selector
        self.skip_on_fail = skip_on_fail

    def select(self, selected):
        super().select(selected)
        sub_selecteds = selected.value

        result_selecteds = []
        for sub_selected in sub_selecteds:
            try:
                result_selected = self.selector.select(sub_selected)
                result_selecteds.append(result_selected)
            except Exception as e:
                if self.skip_on_fail:
                    pass
                else:
                    raise e

        return Selected(result_selecteds, SelectedType.MULTIPLE)

    def toYamlDict(self):
        return {'for_each_selector': {'selector': self.selector.toYamlDict()}}

    def fromYamlDict(yamlDict):
        skip_on_fail = "skip_on_fail" in yamlDict and yamlDict["skip_on_fail"]
        subselector = Selector.fromYamlDict(yamlDict['selector'])
        return ForEachSelector(subselector, skip_on_fail)

# A ZipSelector takes two Selectors as arguments, one of which (keys) will be used to make the keys of a dictionary, the other of which (values) will be used to make the values of that dictionary. May adapt it eventually to allow an arbitrary number of value options, but not sure
# S->M(V)
class ZipSelector(Selector):
    def __init__(self, keys_selector, vals_selector):
        self.keys_selector = keys_selector
        self.vals_selector = vals_selector

    
    def select(self, selected):
        keys = self.keys_selector.select(selected).value
        vals = self.vals_selector.select(selected).value

        if len(keys) != len(vals):
            raise Exception("Keys and Vals provided to ZipSelector must be the same length!")

        keys_are_values = [key.selected_type == SelectedType.VALUE for key in keys]
        vals_are_values = [val.selected_type == SelectedType.VALUE for val in vals]

        key_values = [key.collapsed_value for key in keys]
        val_values = [val.collapsed_value for val in vals]

        mapped = dict(zip(key_values, val_values))

        return Selected(mapped, SelectedType.VALUE)

    def toYamlDict(self):
        return {'zip_selector': {'keys': self.keys_selector.toYamlDict(), 'vals': self.vals_selector.toYamlDict()}}

    def fromYamlDict(yamlDict):
        mapping = {}
        for key, selector in yamlDict.items():
            mapping[key] = Selector.fromYamlDict(selector)

        return ZipSelector(Selector.fromYamlDict(yamlDict['keys']), Selector.fromYamlDict(yamlDict['vals']))





# A MappingSelector is initialized with a dictionary of string keywords to selectors. It takes a Selected Single and returns a Selected Value with the same keywords, mapped to the value selected by their Selector

# error strategy will get upgraded at some point, but can be "mark_none" (to mark the option down as none), "raise" (to raise the error), or "skip" to skip this entire iteration of the map
class MappingSelector(Selector):
    def __init__(self, mapping, error_strategy="skip"):
        self.expected_selected = SelectedType.SINGLE
        self.mapping = mapping
        self.error_strategy = error_strategy

    def select(self, selected):
        super().select(selected)

        mapped = {}
        for key, selector in self.mapping.items():
            try:
                mapped[key] = selector.select(selected).collapsed_value
            except Exception as e:
                if self.error_strategy == "raise":
                    raise e
                elif self.error_strategy == "mark_none":
                    print("Exception raised while reterieving value for", str(key) + ", setting to None: ", e)
                    mapped[key] = None
                else:
                    raise Exception("skip")

        return Selected(mapped, SelectedType.VALUE)

    def toYamlDict(self):
        args_dict = {}
        for key, val in self.mapping.items():
            args_dict[key] = val.toYamlDict()

        return {'mapping_selector': args_dict}

    def fromYamlDict(yamlDict):
        mapping = {}
        for key, selector in yamlDict.items():
            mapping[key] = Selector.fromYamlDict(selector)

        return MappingSelector(mapping)


