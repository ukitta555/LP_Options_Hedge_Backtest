from texttable import Texttable
import latextable
from tabulate import tabulate

table = [["spam",42, 32],["eggs",451, 32],["bacon",0, 32]]
headers = ["", "item", "qty"]

print(tabulate(table, headers, tablefmt="latex"))



def example_1():
    # Example 1 - Basic
    table_1 = Texttable()
    table_1.set_cols_align(["l", "r", "c"])
    table_1.set_cols_valign(["t", "m", "b"])
    table_1.add_rows([["Name", "Age", "Nickname"],
                     ["Mr\nXavier\nHuon", 32, "Xav'"],
                     ["Mr\nBaptiste\nClement", 1, "Baby"],
                     ["Mme\nLouise\nBourgeau", 28, "Lou\n \nLoue"]])
    print('-- Example 1: Basic --')
    print('Texttable Output:')
    print(table_1.draw())
    print('\nLatextable Output:')
    print(latextable.draw_latex(table_1, caption="An example table.", label="table:example_table"))

def example_10():
    # Example 10 - Multicolumn header
    rows = [["R", "A", "B", "C", "D"],
            ["1", "a1", "b1", "c1", "d1"],
            ["2", "a2", "b2", "c2", "d2"],
            ["3", "a3", "b3", "c3", "d3"]]
    multicolumn_header = [("", 1), ("AB", 2), ("CD", 2)]
    print('\n-- Example 10: Multicolumn header --')
    print('Latextable Output:')
    print(latextable.draw_latex(rows, use_booktabs=True, multicolumn_header=multicolumn_header))

def example_11():
    # Example 11 - Multicolumn header with drop column
    rows = [["R", "A", "B", "C", "D"],
            ["1", "a1", "b1", "c1", "d1"],
            ["2", "a2", "b2", "c2", "d2"],
            ["3", "a3", "b3", "c3", "d3"]]
    multicolumn_header = [("", 1), ("AB", 2), ("", 1)]
    print('\n-- Example 11: Multicolumn header with drop column --')
    print('Latextable Output:')
    print(latextable.draw_latex(rows, use_booktabs=True, drop_columns=['C'], multicolumn_header=multicolumn_header))


# example_10()