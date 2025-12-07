import abc

class SystemConverter(abc.ABC):
    def __init__(self, config, source_dir, options):
        self.config = config
        self.source_dir = source_dir
        self.options = options

    @abc.abstractmethod
    def find_inputs(self):
        pass

    @abc.abstractmethod
    def convert(self):
        pass
