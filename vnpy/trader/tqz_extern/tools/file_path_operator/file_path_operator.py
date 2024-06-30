import os


class TQZFilePathOperator:

    @classmethod
    def current_file_path(cls, file=__file__):
        return os.path.abspath(file)

    @classmethod
    def current_file_father_path(cls, file=__file__):
        current_path = os.path.abspath(file)
        return os.path.abspath(os.path.dirname(current_path) + os.path.sep + ".")

    @classmethod
    def current_file_grandfather_path(cls, file=__file__):
        current_path = os.path.abspath(file)
        return os.path.abspath(os.path.dirname(current_path) + os.path.sep + "..")

    @classmethod
    def father_path(cls, source_path=None):
        return os.path.abspath(os.path.dirname(source_path) + os.path.sep + ".")

    @classmethod
    def grandfather_path(cls, source_path=None):
        return os.path.abspath(os.path.dirname(source_path) + os.path.sep + "..")


if __name__ == '__main__':
    pass
