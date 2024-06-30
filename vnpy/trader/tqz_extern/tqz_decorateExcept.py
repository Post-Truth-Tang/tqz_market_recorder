

class TQZDecorateExcept:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args, **kwargs):
        try:
            function_result = self.function(*args, **kwargs)
        except FileNotFoundError as result:
            print("Error: file is not found %s" % result)
        except AttributeError as result:
            print("Error: %s" % result)
        except Exception as result:
            print("unkown Error: %s" % result)
        else:
            return function_result
