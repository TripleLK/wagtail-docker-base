#!/usr/bin/env python3
# sample_scrape.py

import requests
from bs4 import BeautifulSoup
import bs4
from enum import Enum
import copy
from abc import ABC
from copy import deepcopy

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
            print("in collapsed_value, self.value is " + str(self.value))
            return [sub_selected.collapsed_value for sub_selected in self.value]
        else:
            print("in collapsed_value else, self.value is " + str(self.value) + " and selected type is " + str(self.selected_type))
            return self.value



    def __str__(self):
        if self.selected_type != SelectedType.MULTIPLE:
            return str(self.value)
        else:
            return str(self.values())


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
        if (selected.selected_type != self.expected_selected):
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
                "text_selector": TextSelector
            }
            if yamlDict in string_specs_dict:
                return string_specs_dict[yamlDict].fromYamlDict(yamlDict)
        elif isinstance(yamlDict, dict):
            dict_specs_dict = {
                "soup_selector": SoupSelector,
                "indexed_selector": IndexedSelector,
                "attr_selector": AttrSelector,
                "for_each_selector": ForEachSelector,
                "mapping_selector": MappingSelector
            }
            # there will only be one key in the dict, and it'll be the same of the selector
            for key, value in yamlDict.items():
                sole_selector = key
                sole_arguments = value
            return dict_specs_dict[sole_selector].fromYamlDict(sole_arguments)

    def toYamlDict(self):
        pass

# A TextSelector takes a Selected Single and returns the text value within it.
# S->V
class TextSelector(Selector):
    def __init__(self):
        self.expected_selected = SelectedType.SINGLE

    def select(self, selected):
        super().select(selected)
        return Selected(selected.value.get_text(), SelectedType.VALUE)

    def toYamlDict(self):
        return 'text_selector'

    def fromYamlDict(yamlDict):
        return TextSelector()


# A SoupSelector is initialized with a dictionary of attribute names to values. It takes a Selected Single and finds all children of the Single that have those values for those attributes. Use tag_name to target a tag. Has an optional "index" parameter that can be used to specify an index, which will be accessed using an IndexedSelector
# S->M
class SoupSelector(Selector):
    blah = 3
    def __init__(self, attrs, index=None):
        new_attrs = deepcopy(attrs)
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
        attrs_dict = deepcopy(self.attrs)
        if self.tagname != None:
            attrs_dict['tag_name'] = self.tagname

        args_dict['attrs'] = attrs_dict

        if self.index != None:
            args_dict['index'] = self.index

        return {'soup_selector': args_dict}

    def fromYamlDict(yamlDict):
        if 'index' in yamlDict:
            return SoupSelector(yamlDict['attrs'], index=yamlDict['index'])

        attrs_dict = deepcopy(yamlDict['attrs'])
        tagName = None
        if 'tag_name' in attrs_dict:
            tagName = attrs_dict.pop('tag_name')


        return SoupSelector(yamlDict['attrs'], )




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


# A SeriesSelector is initialized with a list of Selectors. It takes a Selected of the type expected by its first selector and calls the selectors in sequence, returning the final value.
# Variable type, depends on selectors assigned to it
class SeriesSelector(Selector):
    def __init__(self, selectors):
        self.expected_selected = selectors[0].expected_selected
        self.selectors = selectors

    def select(self, selected):
        super().select(selected)

        current = selected
        series_copy = deepcopy(self.selectors)
        while series_copy != []:
            current = series_copy.pop(0).select(current)

        return current

    def toYamlDict(self):
        return [selector.toYamlDict() for selector in self.selectors]

    def fromYamlDict(yamlDictList):
        print("dict:" + str(yamlDictList))
        subSelectors = [Selector.fromYamlDict(subYamlDict) for subYamlDict in yamlDictList]
        return SeriesSelector(subSelectors)


# A ForEachSelector is initialized with a Selector of any type (including a SeriesSelector). It takes a Selected Multiple and returns a Selected Multiple, where each Selected in the returned Selected Multiple is the result of applying the selector to an element of the inputted Selected Multiple (in order)
# M->M
class ForEachSelector(Selector):
    def __init__(self, selector):
        self.expected_selected = SelectedType.MULTIPLE
        self.selector = selector

    def select(self, selected):
        super().select(selected)
        sub_selecteds = selected.value

        result_selecteds = []
        for sub_selected in sub_selecteds:
            result_selected = self.selector.select(sub_selected)
            result_selecteds.append(result_selected)

        return Selected(result_selecteds, SelectedType.MULTIPLE)

    def toYamlDict(self):
        return {'for_each_selector': {'selector': self.selector.toYamlDict()}}

    def fromYamlDict(yamlDict):
        subselector = Selector.fromYamlDict(yamlDict['selector'])
        return ForEachSelector(subselector)


# A MappingSelector is initialized with a dictionary of string keywords to selectors. It takes a Selected Single and returns a Selected Value with the same keywords, mapped to the value selected by their Selector
class MappingSelector(Selector):
    def __init__(self, mapping):
        self.expected_selected = SelectedType.SINGLE
        self.mapping = mapping

    def select(self, selected):
        super().select(selected)

        mapped = {}
        for key, selector in self.mapping.items():
            try:
                mapped[key] = selector.select(selected).collapsed_value
            except Exception as e:
                print("Exception raised while reterieving value for", str(key) + ", setting to None: ", e)
                mapped[key] = None

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


