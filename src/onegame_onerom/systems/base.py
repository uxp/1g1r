import glob
import os
import shutil
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


# Generalized processor for copy-only systems
class CopyProcessor(SystemProcessor):
    def find_inputs(self):
        pattern = os.path.join(self.source_dir, self.config.get('file_pattern', '*'))
        return glob.glob(pattern)

    def process(self):
        inputs = self.find_inputs()
        verbose = self.options.get('verbose', False)
        dry_run = self.options.get('dry_run', False)
        if verbose:
            print(f"Found files: {len(inputs)}")
        for src_file in inputs:
            dest_file = os.path.join(self.dest_dir, os.path.basename(src_file))
            if verbose:
                print(f"Copying {src_file} to {dest_file}")
            if not dry_run:
                if os.path.exists(dest_file) and not self.options.get('force', False):
                    print(f"Destination file {dest_file} already exists, skipping.")
                    continue
                os.makedirs(self.dest_dir, exist_ok=True)
                shutil.copy2(src_file, dest_file)
            else:
                print(f"[DRY-RUN] Would copy {src_file} to {dest_file}")
        print("Copy-only processing complete.")