#!/usr/bin/env python3
# apps/scrapers/Selectors.py
# Legacy file - imports from the new modular structure

"""
DEPRECATION NOTICE:
This file is provided for backward compatibility.
New code should import directly from the 'selectors' package.

Example:
    from apps.scrapers.selectors import CSSSelector, TextSelector
"""

import warnings

warnings.warn(
    "The monolithic Selectors.py file is deprecated. "
    "Please import from apps.scrapers.selectors instead.",
    DeprecationWarning,
    stacklevel=2
)

from enum import Enum
from bs4 import BeautifulSoup
import bs4
import re
from copy import deepcopy
import yaml
from abc import ABC, abstractmethod
# Import from the new modular structure
from .selectors.base import SelectedType, Selected, Selector
from .selectors.text_selector import TextSelector
from .selectors.html_selector import HtmlSelector
from .selectors.css_selector import CSSSelector
from .selectors.soup_selector import SoupSelector
from .selectors.indexed_selector import IndexedSelector
from .selectors.attr_selector import AttrSelector
from .selectors.split_selector import SplitSelector
from .selectors.series_selector import SeriesSelector
from .selectors.print_selector import PrintSelector
from .selectors.for_each_selector import ForEachSelector
from .selectors.zip_selector import ZipSelector
from .selectors.mapping_selector import MappingSelector
from .selectors.plain_text_selector import PlainTextSelector
from .selectors.concat_selector import ConcatSelector
from .selectors.file_selector import FileSelector
from .selectors.value_to_single_selector import ValueToSingleSelector

# Re-export all classes for backward compatibility
__all__ = [
    'SelectedType', 'Selected', 'Selector',
    'TextSelector', 'HtmlSelector', 'CSSSelector', 'SoupSelector',
    'IndexedSelector', 'AttrSelector', 'SplitSelector',
    'SeriesSelector', 'PrintSelector', 'ForEachSelector',
    'ZipSelector', 'MappingSelector', 'PlainTextSelector',
    'ConcatSelector', 'FileSelector', 'ValueToSingleSelector'
]


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
                raise TypeError(str(type(self)) + " expects a Selected of type " + " or ".join([exspel.name for exspel in self.expected_selected]) + ", but received " + selected.selected_type.name)
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

        # Ensure the value is a Tag or BeautifulSoup object before calling prettify
        if isinstance(selected.value, (bs4.element.Tag, BeautifulSoup)):
             html_content = selected.value.prettify()
        else:
             # Handle cases like NavigableString - just convert to string
             html_content = str(selected.value)

        return Selected(html_content.strip(), SelectedType.VALUE)

    def toYamlDict(self):
        return 'html_selector'

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        return HtmlSelector()

# Creates a selector based on a secondary file. Allows for neatening of files
class FileSelector(Selector):
    def __init__(self, file_path):
        self.file_path = file_path
        self._selector = None # Lazy load selector

    @property
    def selector(self):
         if self._selector is None:
             self._selector = Selector.fromFilePath(self.file_path)
             if self._selector is None:
                 # Raise an error if loading failed, providing context
                 raise RuntimeError(f"Failed to load selector from file: {self.file_path}")
         return self._selector


    def select(self, selected):
        # Access the selector via the property to ensure it's loaded
        return self.selector.select(selected)

    def toYamlDict(self):
        return self.selector.toYamlDict()

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'file_path' not in yamlDict:
            raise ValueError("FileSelector YAML requires a 'file_path' key.")
        return FileSelector(yamlDict['file_path'])

class ConcatSelector(Selector):
    def __init__(self, first, second):
        # No expected input type, depends on the sub-selectors
        self.first = first
        self.second = second
        # print("concat inited") # Removed print

    def select(self, selected):
        # Selectors are applied to the *same* input selected object
        first_result = self.first.select(deepcopy(selected)) # Use deepcopy if selectors modify input
        second_result = self.second.select(deepcopy(selected))

        # Ensure results are VALUE type or convert them
        # This might need more sophisticated handling depending on desired behavior
        val1 = first_result.collapsed_value if first_result.selected_type == SelectedType.VALUE else str(first_result.collapsed_value)
        val2 = second_result.collapsed_value if second_result.selected_type == SelectedType.VALUE else str(second_result.collapsed_value)


        return Selected(str(val1) + str(val2), SelectedType.VALUE)

    def toYamlDict(self):
        # Ensure keys are strings
        return {"concat_selector": {'first': self.first.toYamlDict(), 'second': self.second.toYamlDict()}}

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        # print("About to init concat") # Removed print
        if 'first' not in yamlDict or 'second' not in yamlDict:
             raise ValueError("ConcatSelector YAML requires 'first' and 'second' keys.")
        return ConcatSelector(Selector.fromYamlDict(yamlDict['first']), Selector.fromYamlDict( yamlDict['second'] ))


# A SoupSelector is initialized with a dictionary of attribute names to values. It takes a Selected Single and finds all children of the Single that have those values for those attributes. Use tag_name to target a tag. Has an optional "index" parameter that can be used to specify an index, which will be accessed using an IndexedSelector
# S->M
class SoupSelector(Selector):
    def __init__(self, attrs, re_attrs=None, index=None):
        self.expected_selected = SelectedType.SINGLE # Expects a single Tag/Soup object
        self.original_attrs = deepcopy(attrs) if attrs else {}
        self.original_re_attrs = deepcopy(re_attrs) if re_attrs else None
        self.index = index

        new_attrs = deepcopy(self.original_attrs)
        self.tagname = new_attrs.pop("tag_name", None) # Use pop with default

        # compile any regex type attributes
        if self.original_re_attrs:
             if not isinstance(self.original_re_attrs, dict):
                 raise TypeError("re_attrs must be a dictionary")
             for key, val in self.original_re_attrs.items():
                 try:
                     compiled = re.compile(val)
                     new_attrs[key] = compiled # Add compiled regex to attrs for find_all
                 except re.error as e:
                     raise ValueError(f"Invalid regex for key '{key}': {val}. Error: {e}")


        self.expected_selected = SelectedType.SINGLE
        self.tagname = new_attrs.pop("tag_name") if "tag_name" in attrs else None
        self.attrs = new_attrs
        self.index=index

    def select(self, selected):
        super().select(selected)

        # Ensure we are working with a Tag or BeautifulSoup object
        if not isinstance(selected.value, (bs4.element.Tag, BeautifulSoup)):
             raise TypeError(f"SoupSelector requires a bs4.element.Tag or BeautifulSoup object, got {type(selected.value)}")


        values = selected.value.find_all(name=self.tagname, attrs=self.attrs)


        selecteds = Selected([Selected(val, SelectedType.SINGLE) for val in values], SelectedType.MULTIPLE)

        if self.index is not None:
             # Import locally or ensure IndexedSelector is available
             from .selectors.indexed_selector import IndexedSelector # Adjust import path
             return IndexedSelector(self.index).select(selecteds)
        return selecteds

    def toYamlDict(self):
        args_dict = {}
        # Only include 'attrs' if it's not empty
        if self.original_attrs:
             args_dict['attrs'] = self.original_attrs

        if self.index is not None:
            args_dict['index'] = self.index

        if self.original_re_attrs:
            args_dict['re_attrs'] = self.original_re_attrs

        # Handle case where attrs might be empty if only tag_name was used initially
        # (though tag_name is handled separately now)
        if not args_dict:
             # If only tag_name was provided, represent it within attrs for consistency?
             # Or handle tag_name explicitly in YAML? Let's keep it simple for now.
             # If attrs and re_attrs were empty, maybe just return the tag_name?
             # Current logic handles original_attrs, let's stick to that.
             pass # If nothing else, the dict remains empty, leading to {'soup_selector': {}}


        return {'soup_selector': args_dict}

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        attrs_dict = deepcopy(yamlDict.get('attrs', {})) # Use .get with default
        re_attrs_dict = deepcopy(yamlDict.get('re_attrs')) # Use .get, defaults to None
        index = yamlDict.get('index') # Use .get, defaults to None

        # Basic validation
        if not isinstance(attrs_dict, dict):
             raise TypeError("'attrs' must be a dictionary in SoupSelector YAML.")
        if re_attrs_dict is not None and not isinstance(re_attrs_dict, dict):
             raise TypeError("'re_attrs' must be a dictionary in SoupSelector YAML.")
        if index is not None and not isinstance(index, int):
             raise TypeError("'index' must be an integer in SoupSelector YAML.")


        return SoupSelector(attrs=attrs_dict, re_attrs=re_attrs_dict, index=index)




# An IndexedSelector is initialized with an index n. It takes a Selected Multiple and returns the nth element of it.
# M->S
class IndexedSelector(Selector):
    def __init__(self, index):
        self.expected_selected = SelectedType.MULTIPLE
        if not isinstance(index, int):
             raise TypeError("Index must be an integer.")
        self.index = index

    def select(self, selected):
        super().select(selected)

        return selected.value[self.index]

    def toYamlDict(self):
        return {'indexed_selector': {'index': self.index}}

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'index' not in yamlDict:
             raise ValueError("IndexedSelector YAML requires an 'index' key.")
        if not isinstance(yamlDict['index'], int):
             raise TypeError("IndexedSelector 'index' must be an integer.")
        return IndexedSelector(yamlDict['index'])



# An AttrSelector selects a given attribute from a Selected Single
# S->V
class AttrSelector(Selector):
    def __init__(self, attr):
        self.expected_selected = SelectedType.SINGLE
        if not isinstance(attr, str) or not attr:
             raise ValueError("Attribute name must be a non-empty string.")
        self.attr = attr

    def select(self, selected):
        super().select(selected)
        # Ensure selected.value is a Tag object, as NavigableString, etc., don't have attrs
        if not isinstance(selected.value, bs4.element.Tag):
             raise TypeError(f"AttrSelector requires a bs4.element.Tag, but received {type(selected.value)}.")

        try:
             # Use .get() for safer access, returning None if attr doesn't exist
             attr_value = selected.value.get(self.attr)
             # Return None as a VALUE, consistent with mapping behavior perhaps
             return Selected(attr_value, SelectedType.VALUE)
             # Or raise KeyError if the attribute *must* exist:
             # return Selected(selected.value[self.attr], SelectedType.VALUE)
        except KeyError:
            # This block is only needed if using direct access `selected.value[self.attr]`
            raise KeyError(f"Attribute '{self.attr}' not found in tag.")


    def toYamlDict(self):
        return {'attr_selector': {'attr': self.attr}}

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'attr' not in yamlDict:
            raise ValueError("AttrSelector YAML requires an 'attr' key.")
        if not isinstance(yamlDict['attr'], str) or not yamlDict['attr']:
             raise ValueError("AttrSelector 'attr' must be a non-empty string.")
        return AttrSelector(yamlDict['attr'])

# Split Selector takes a Selected Single (which it will turn to HTML) or a Selected Value. It splits that string by the string delimiter, and returns a Selected Multiple of Selected Values.
class SplitSelector(Selector):
    def __init__(self, delimiter):
        self.expected_selected = [SelectedType.VALUE, SelectedType.SINGLE]
        if not isinstance(delimiter, str):
             raise TypeError("Delimiter must be a string.")
        self.delimiter = delimiter

    def select(self, selected):
        super().select(selected) # Validate input type

        # Determine the text representation based on the input type
        if selected.selected_type == SelectedType.SINGLE:
             # Need to handle different types within SINGLE carefully
             if isinstance(selected.value, (bs4.element.Tag, BeautifulSoup)):
                 # Option 1: Use text content
                 # text_rep = selected.value.get_text(separator=' ', strip=True)
                 # Option 2: Use HTML content (as originally implied)
                 text_rep = str(selected.value.prettify())
             else: # Assume NavigableString or similar
                 text_rep = str(selected.value)
        else: # VALUE type
             text_rep = str(selected.value) # Ensure it's a string

        split_up = text_rep.split(self.delimiter)

        # Return a MULTIPLE of VALUEs (strings), not SINGLEs (soups)
        portions = [Selected(portion.strip(), SelectedType.VALUE) for portion in split_up if portion.strip()] # Added strip and filter empty


        return Selected(portions, SelectedType.MULTIPLE)

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'delimiter' not in yamlDict:
            raise ValueError("SplitSelector YAML requires a 'delimiter' key.")
        if not isinstance(yamlDict['delimiter'], str):
             raise TypeError("SplitSelector 'delimiter' must be a string.")
        return SplitSelector(yamlDict['delimiter'])

    def toYamlDict(self):
        return {"split_selector": {"delimiter": self.delimiter}}


# A SeriesSelector is initialized with a list of Selectors. It takes a Selected of the type expected by its first selector and calls the selectors in sequence, returning the final value.
# Variable type, depends on selectors assigned to it
class SeriesSelector(Selector):
    def __init__(self, selectors):
        if not isinstance(selectors, list) or not all(isinstance(s, Selector) for s in selectors):
            raise TypeError("SeriesSelector requires a list of Selector instances.")
        self.selectors = selectors
        # Determine expected input type from the first selector in the series
        if selectors:
             self.expected_selected = selectors[0].expected_selected
        else:
             self.expected_selected = None # If no selectors, accepts anything (becomes identity)


    def select(self, selected):
        # Initial validation based on the *first* selector's expectation
        super().select(selected)

        current = selected
        series_copy = deepcopy(self.selectors)
        while series_copy != []:
            current = series_copy.pop(0).select(current)

        return current

    def toYamlDict(self):
        return [selector.toYamlDict() for selector in self.selectors]

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDictList):
        if not isinstance(yamlDictList, list):
            raise TypeError("SeriesSelector expects a YAML list.")
        subSelectors = [Selector.fromYamlDict(subYamlDict) for subYamlDict in yamlDictList]
        return SeriesSelector(subSelectors)

class PrintSelector(Selector):
    def __init__(self, message, print_selected=False):
        # No specific expected type, acts as pass-through
        self.expected_selected = None
        self.message = message
        self.print_selected = print_selected

    def select(self, selected):
        # No call to super().select() as expected_selected is None

        # Use logging instead of print for better control in applications
        import logging
        log = logging.getLogger(__name__) # Or a more specific logger name
        log.info(f"PrintSelector: {self.message}") # Use INFO or DEBUG level

        if self.print_selected:
           try:
                # Attempt to get a collapsed value for logging
                collapsed = selected.collapsed_value
                log.info(f"PrintSelector report.\n  Selected Type: {selected.selected_type}\n  Collapsed Value: {collapsed}")
           except Exception as e:
                # Log safely if collapsing fails
                log.info(f"PrintSelector report.\n  Selected Type: {selected.selected_type}\n  Value (could not collapse): {selected.value}\n  Collapse Error: {e}")


        return selected # Pass the original selected object through

    def toYamlDict(self):
        yaml_dict = {"message": self.message}
        if self.print_selected:
             yaml_dict["print_selected"] = True
        return {"print_selector": yaml_dict}


    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'message' not in yamlDict:
             raise ValueError("PrintSelector YAML requires a 'message' key.")
        return PrintSelector(
            yamlDict["message"],
            print_selected=yamlDict.get("print_selected", False) # Use .get with default
        )

# A ForEachSelector is initialized with a Selector of any type (including a SeriesSelector). It takes a Selected Multiple and returns a Selected Multiple, where each Selected in the returned Selected Multiple is the result of applying the selector to an element of the inputted Selected Multiple (in order)
# M->M
class ForEachSelector(Selector):
    def __init__(self, selector, skip_on_fail=False):
        self.expected_selected = SelectedType.MULTIPLE
        if not isinstance(selector, Selector):
             raise TypeError("ForEachSelector requires a Selector instance.")
        self.selector = selector
        self.skip_on_fail = skip_on_fail

    def select(self, selected):
        super().select(selected) # Validate input is MULTIPLE
        sub_selecteds = selected.value

        if not isinstance(sub_selecteds, list):
             raise TypeError("ForEachSelector input Selected's value must be a list.")


        result_selecteds = []
        for i, sub_selected in enumerate(sub_selecteds):
             # Ensure each item is a Selected object before processing
             if not isinstance(sub_selected, Selected):
                  err_msg = f"Item at index {i} in ForEachSelector input list is not a Selected object (type: {type(sub_selected)})."
                  if self.skip_on_fail:
                      print(f"Warning: {err_msg} Skipping.") # Or log warning
                      continue
                  else:
                      raise TypeError(err_msg)

             try:
                # Apply the sub-selector to the current item
                # Use deepcopy if the selector might modify its input and affect later iterations
                # result_selected = self.selector.select(deepcopy(sub_selected))
                result_selected = self.selector.select(sub_selected)
                result_selecteds.append(result_selected)
             except Exception as e:
                if self.skip_on_fail:
                    # Log the skipped item and error for debugging
                    import logging
                    log = logging.getLogger(__name__)
                    log.warning(f"ForEachSelector skipped item at index {i} due to error: {e}", exc_info=True) # Include stack trace
                    pass # Skip this item
                else:
                    # Re-raise the exception with more context
                    raise type(e)(f"Error processing item at index {i} in ForEachSelector: {e}") from e


        return Selected(result_selecteds, SelectedType.MULTIPLE)

    def toYamlDict(self):
        yaml_dict = {'selector': self.selector.toYamlDict()}
        if self.skip_on_fail: # Only include if true
             yaml_dict['skip_on_fail'] = True
        return {'for_each_selector': yaml_dict}


    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'selector' not in yamlDict:
             raise ValueError("ForEachSelector YAML requires a 'selector' key.")
        skip_on_fail = yamlDict.get("skip_on_fail", False) # Use .get with default
        if not isinstance(skip_on_fail, bool):
             raise TypeError("ForEachSelector 'skip_on_fail' must be a boolean.")

        subselector = Selector.fromYamlDict(yamlDict['selector'])
        return ForEachSelector(subselector, skip_on_fail)

# A ZipSelector takes two Selectors as arguments, one of which (keys) will be used to make the keys of a dictionary, the other of which (values) will be used to make the values of that dictionary. May adapt it eventually to allow an arbitrary number of value options, but not sure
# S->M(V) ? -> Should likely return VALUE (dict)
class ZipSelector(Selector):
    def __init__(self, keys_selector, vals_selector):
         # Input type depends on sub-selectors, cannot strictly define here.
         # Could potentially analyze sub-selectors if needed.
        self.expected_selected = None # Or SelectedType.SINGLE if sub-selectors expect that?
        if not isinstance(keys_selector, Selector) or not isinstance(vals_selector, Selector):
             raise TypeError("ZipSelector requires two Selector instances.")
        self.keys_selector = keys_selector
        self.vals_selector = vals_selector


    def select(self, selected):
        # No super().select() call as expected_selected is None or variable.
        # Sub-selectors will validate their own inputs.

        # Apply selectors to copies if they might modify the input
        keys_result = self.keys_selector.select(deepcopy(selected))
        vals_result = self.vals_selector.select(deepcopy(selected))

        # Expect results to be MULTIPLE type
        if keys_result.selected_type != SelectedType.MULTIPLE:
             raise TypeError(f"Keys selector in ZipSelector must return MULTIPLE, got {keys_result.selected_type}")
        if vals_result.selected_type != SelectedType.MULTIPLE:
             raise TypeError(f"Values selector in ZipSelector must return MULTIPLE, got {vals_result.selected_type}")


        keys = keys_result.value
        vals = vals_result.value

        if len(keys) != len(vals):
            raise ValueError(f"Keys and Vals selected by ZipSelector must be the same length ({len(keys)} != {len(vals)}).") # Changed Exception to ValueError


        # Extract collapsed values. Ensure keys are hashable.
        try:
             # Use collapsed_value which handles nested structures if necessary
            key_values = [k.collapsed_value for k in keys]
            val_values = [v.collapsed_value for v in vals]
             # Further check if keys are suitable (e.g., strings, numbers) might be needed depending on usage
             # for k in key_values:
             #    if not isinstance(k, (str, int, float, bool)): # Example check
             #        raise TypeError(f"Dictionary keys must be immutable and hashable, got {type(k)}")
        except Exception as e:
            raise TypeError(f"Failed to extract or collapse key/value for zipping: {e}") from e


        # Create the dictionary
        mapped = dict(zip(key_values, val_values))

        # Return as a VALUE type containing the dictionary
        return Selected(mapped, SelectedType.VALUE)

    def toYamlDict(self):
        return {'zip_selector': {'keys': self.keys_selector.toYamlDict(), 'vals': self.vals_selector.toYamlDict()}}

    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
        if 'keys' not in yamlDict or 'vals' not in yamlDict:
             raise ValueError("ZipSelector YAML requires 'keys' and 'vals' keys.")

        # The original implementation had incorrect logic here, trying to iterate yamlDict items.
        # It should directly use the 'keys' and 'vals' sub-dictionaries.
        keys_sub_selector = Selector.fromYamlDict(yamlDict['keys'])
        vals_sub_selector = Selector.fromYamlDict(yamlDict['vals'])


        return ZipSelector(keys_sub_selector, vals_sub_selector)





# A MappingSelector is initialized with a dictionary of string keywords to selectors. It takes a Selected Single and returns a Selected Value with the same keywords, mapped to the value selected by their Selector

# error strategy will get upgraded at some point, but can be "mark_none" (to mark the option down as none), "raise" (to raise the error), or "skip" to skip this entire iteration of the map
class MappingSelector(Selector):
    VALID_ERROR_STRATEGIES = ["skip", "raise", "mark_none"] # Class constant

    def __init__(self, mapping, error_strategy="raise"): # Default to raise for clarity
        self.expected_selected = SelectedType.SINGLE # Usually applied to a single item/context
        if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, Selector) for k, v in mapping.items()):
             raise TypeError("MappingSelector requires a dict mapping string keys to Selector instances.")
        self.mapping = mapping

        if error_strategy not in self.VALID_ERROR_STRATEGIES:
             raise ValueError(f"Invalid error_strategy '{error_strategy}'. Must be one of {self.VALID_ERROR_STRATEGIES}")
        self.error_strategy = error_strategy


    def select(self, selected):
        super().select(selected)

        mapped = {}
        for key, selector in self.mapping.items():
            try:
                 # Apply selector to a deep copy to prevent side effects between mapping items
                result = selector.select(deepcopy(selected))
                # Store the collapsed value in the result dictionary
                mapped[key] = result.collapsed_value
            except Exception as e:
                if self.error_strategy == "raise":
                    # Re-raise with context about the key being processed
                    raise type(e)(f"Error processing key '{key}' in MappingSelector: {e}") from e
                elif self.error_strategy == "mark_none":
                    # Log the error for debugging purposes
                    import logging
                    log = logging.getLogger(__name__)
                    log.warning(f"MappingSelector: Exception raised while retrieving value for key '{key}', setting to None.", exc_info=True) # Include stack trace
                    mapped[key] = None
                elif self.error_strategy == "skip":
                     # This strategy doesn't make sense when processing a single item's map.
                     # It's more relevant in a ForEach context containing a MappingSelector.
                     # If an error occurs here with 'skip', the entire mapping for this *single* input fails.
                     # Let's re-raise as if 'raise' was chosen for clarity within MappingSelector itself.
                     # Or maybe it means skip *this key*? Let's assume skip means fail the whole map for this input.
                     raise Exception(f"MappingSelector encountered error on key '{key}' with 'skip' strategy. Aborting map.") from e
                 # The original code had a bare 'raise Exception("skip")' which was ambiguous.


        # Return the resulting dictionary wrapped in a VALUE Selected
        return Selected(mapped, SelectedType.VALUE)

    def toYamlDict(self):
        args_dict = {}
        for key, val in self.mapping.items():
            args_dict[key] = val.toYamlDict()

        # Only include error_strategy if it's not the default ('raise')
        yaml_outer = {'mapping_selector': args_dict}
        if self.error_strategy != "raise":
             # Add strategy to the inner dict alongside the mapping? Or outer?
             # Let's put it alongside the mapping definition.
             args_dict['_error_strategy'] = self.error_strategy # Use a distinct key maybe?

        # Alternative: put strategy at the same level as the mapping dict
        # yaml_outer = {'mapping_selector': {'mapping': args_dict}}
        # if self.error_strategy != "raise":
        #      yaml_outer['mapping_selector']['error_strategy'] = self.error_strategy

        # Let's stick to the first approach for now (putting it inside the main dict)
        # Reverting: Simpler to put it inside the mapping_selector dict directly if needed
        final_yaml_dict = {}
        for key, val in self.mapping.items():
            final_yaml_dict[key] = val.toYamlDict()

        outer_wrapper = {}
        outer_wrapper['mapping'] = final_yaml_dict # Key name 'mapping' for clarity?
        if self.error_strategy != "raise":
             outer_wrapper['error_strategy'] = self.error_strategy

        return {'mapping_selector': outer_wrapper}


    @staticmethod # Added staticmethod decorator
    def fromYamlDict(yamlDict):
         # Adapt based on the chosen toYamlDict structure
        if 'mapping' not in yamlDict:
             # Fallback for old format? Or raise error? Let's assume new format.
             raise ValueError("MappingSelector YAML expects a 'mapping' key containing the selectors map.")

        mapping_definition = yamlDict['mapping']
        error_strategy = yamlDict.get('error_strategy', "raise") # Get strategy, default to raise


        if not isinstance(mapping_definition, dict):
             raise TypeError("MappingSelector 'mapping' value must be a dictionary.")
        if error_strategy not in MappingSelector.VALID_ERROR_STRATEGIES:
             raise ValueError(f"Invalid 'error_strategy' in MappingSelector YAML: {error_strategy}")


        mapping = {}
        for key, selector_yaml in mapping_definition.items():
            if not isinstance(key, str):
                 raise TypeError(f"MappingSelector keys must be strings, got {type(key)}")
            mapping[key] = Selector.fromYamlDict(selector_yaml)


        return MappingSelector(mapping, error_strategy=error_strategy)



