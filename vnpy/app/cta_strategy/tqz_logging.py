import logging
import os

from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator


class TQZLogging:

    __strategy_bug_fold = TQZFilePathOperator.current_file_father_path(file=__file__) + f'/strategy_bug_log'

    __formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    @classmethod
    def write_bug_log(cls, vt_symbol: str, message: str):

        if os.path.exists(cls.__strategy_bug_fold) is False:
            os.makedirs(cls.__strategy_bug_fold)

        symbol = vt_symbol.split('.')[0]
        log_path = cls.__strategy_bug_fold + f'/{symbol}.log'

        logger = logging.getLogger(vt_symbol)
        logger.setLevel(level=logging.DEBUG)

        handler = logging.FileHandler(log_path)  # filename
        handler.setLevel(logging.INFO)
        handler.setFormatter(cls.__formatter)

        logger.addHandler(handler)
        logger.info(message)  # message
        logger.removeHandler(handler)


if __name__ == '__main__':
    # TQZLogging.write_bug_log(vt_symbol="rb2201.SHFE", message="this is a test.")
    pass
