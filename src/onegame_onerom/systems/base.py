import abc

class SystemProcessor(abc.ABC):
    def __init__(self, config, source_dir, dest_dir, options):
        self.config = config
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.options = options

    @abc.abstractmethod
    def find_inputs(self):
        pass

    @abc.abstractmethod
    def process(self):
        pass
