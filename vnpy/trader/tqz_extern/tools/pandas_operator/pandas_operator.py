
import pandas

class TQZPandas:

    @classmethod
    def pre_set(cls, max_column_width=100, width=1000):
        # show all columns
        pandas.set_option('display.max_columns', None)

        # show all rows
        pandas.set_option('display.max_rows', None)

        # set display width of value: 100, default is 50
        pandas.set_option('max_colwidth', max_column_width)

        # avoid linefeed
        pandas.set_option('display.width', width)


TQZPandas.pre_set()
