import pytest
from bs4 import BeautifulSoup
import bs4
from Selectors import Selected, SelectedType

STSingle = SelectedType.SINGLE
STMultiple = SelectedType.MULTIPLE
STVALUE = SelectedType.VALUE

class TestSelectedSingle:
    def setup_method(self, method):
        html = """<div>Blah</div>"""
        soup = BeautifulSoup(html, "html.parser")
        self.selected_tag = soup.find_all('div')[0]
        self.selected_single = Selected(self.selected_tag, STSingle)

    def test_selected_single_valid_initialization(self):
        assert self.selected_tag == self.selected_single.value
        assert self.selected_single.selected_type == STSingle

    def test_selected_single_initialization_invalid(self):
        with pytest.raises(Exception, match='Selecteds of type Single') as e:
            invalid_selected_single = Selected(3, STSingle)
