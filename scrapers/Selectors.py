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

    def values(self):
        if self.selected_type != SelectedType.MULTIPLE:
            return TypeError("Only Selecteds of type MULTIPLE may use the values method")
        return [str(sub_selected.value) for sub_selected in self.value]

    def __str__(self):
        if self.selected_type != SelectedType.MULTIPLE:
            return str(self.value)
        else:
            return str(self.values())

    def __validate_selected_type(self):
        if self.selected_type == SelectedType.VALUE:
            return None
        elif self.selected_type == SelectedType.SINGLE:
            if isinstance(self.value, bs4.element.Tag) or isinstance(self.value, bs4.BeautifulSoup):
                return None
            else:
                return TypeError("Selecteds of type Single must be Tags or the root of the dom! Your value: " + str(self.value) + ", which has a type of " + str(type(self.value)))
        elif self.selected_type == SelectedType.MULTIPLE:
            if isinstance(self.value, list) and all([isinstance(el, Selected) for el in self.value]):
                return None
            else:
                return TypeError("Selecteds of type Multiple must be lists of other Selecteds")


class Selector(ABC):
    def validate_selected_type(self, selected):
        if (selected.selected_type != self.expected_selected):
            raise TypeError(str(type(self)) + " expects a Selected of type " + self.expected_selected.name + ", but received " + selected.selected_type.name)

    def __call__(self, selected):
        return self.select(selected)

    def select(self, selected):
        self.validate_selected_type(selected)

# A TextSelector takes a Selected Single and returns the text value within it.
# S->V
class TextSelector(Selector):
    def __init__(self):
        self.expected_selected = SelectedType.SINGLE

    def select(self, selected):
        super().select(selected)
        return Selected(selected.value.get_text(), SelectedType.VALUE)


# A SoupSelector is initialized with a dictionary of attribute names to values. It takes a Selected Single and finds all children of the Single that have those values for those attributes. Use tag_name to target a tag. Has an optional "index" parameter that can be used to specify an index, which will be accessed using an IndexedSelector
# S->M
class SoupSelector(Selector):
    def __init__(self, attrs, index=None):
        self.expected_selected = SelectedType.SINGLE
        self.tagname = attrs["tag_name"] if "tag_name" in attrs else None
        self.attrs = attrs
        self.index=index

    def select(self, selected):
        super().select(selected)

        if self.tagname:
            values = selected.value.find_all(self.tagname, attrs=self.attrs)
        else:
            values = selected.value.find_all(attrs=self.attrs)

        selecteds = Selected([Selected(val, SelectedType.SINGLE) for val in values], SelectedType.MULTIPLE)
        if self.index != None:
            return IndexedSelector(self.index).select(selecteds)
        return selecteds


# An IndexedSelector is initialized with an index n. It takes a Selected Multiple and returns the nth element of it.
# M->S
class IndexedSelector(Selector):
    def __init__(self, index):
        self.expected_selected = SelectedType.MULTIPLE
        self.index = index

    def select(self, selected):
        super().select(selected)

        return selected.value[self.index]



# An AttrSelector selects a given attribute from a Selected Single
# S->V
class AttrSelector(Selector):
    def __init__(self, attr):
        self.expected_selected = SelectedType.SINGLE
        self.attr = attr

    def select(self, selected):
        super().select(selected)
        return Selected(selected.value[self.attr], SelectedType.VALUE)


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


# A ForEachSelector is initialized with a Selector of any type (including a SeriesSelector). It takes a Selected Multiple and returns a Selected Multiple, where each Selected in the returned Selected Multiple is the result of applying the selector to an element of the inputted Selected Multiple (in order)
# M->M
class ForEachSelector(Selector):
    def __init__(self, selector):
        self.expected_selected = SelectedType.MULTIPLE
        self.selector = selector

    def select(self, selected):
        sub_selecteds = selected.value

        result_selecteds = []
        for sub_selected in sub_selecteds:
            result_selected = self.selector.select(sub_selected)
            result_selecteds.append(result_selected)

        return Selected(result_selecteds, SelectedType.MULTIPLE)
