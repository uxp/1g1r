import glob
import os
from .base import SystemConverter

class PSXConverter(SystemConverter):
    def find_inputs(self):
        import re
        pattern = os.path.join(self.source_dir, self.config.get('input_pattern', '*.zip'))
        files = glob.glob(pattern)
        # Group files by game name, handling multi-disk
        game_map = {}
        disk_regex = re.compile(r'^(?P<name>.+?)\s*\(Disk\s*(?P<disk>\d+)\)\.zip$', re.IGNORECASE)
        for f in files:
            base = os.path.basename(f)
            m = disk_regex.match(base)
            if m:
                name = m.group('name').strip()
                disk_num = int(m.group('disk'))
                if name not in game_map:
                    game_map[name] = {'name': name, 'disks': []}
                game_map[name]['disks'].append({'file': f, 'disk_num': disk_num})
            else:
                # Single disk game
                name = os.path.splitext(base)[0]
                game_map[name] = {'name': name, 'disks': [{'file': f, 'disk_num': 1}]}
        # Sort disks for each game
        for g in game_map.values():
            g['disks'].sort(key=lambda d: d['disk_num'])
        return list(game_map.values())

    def extract_zip(self, zip_path, extract_to):
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

    def convert(self):
        import tempfile
        import subprocess
        inputs = self.find_inputs()
        print(f"Found PSX games: {[g['name'] for g in inputs]}")
        verbose = self.options.get('verbose', False)
        debug = self.options.get('debug', False)
        dry_run = self.options.get('dry_run', False)
        for game in inputs:
            game_name = game['name']
            disks = game['disks']
            if verbose or debug:
                print(f"Processing game: {game_name} with {len(disks)} disk(s)")
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_cues = []
                for disk in disks:
                    zip_file = disk['file']
                    if verbose or debug:
                        print(f"Extracting {zip_file} to {temp_dir}")
                    if not dry_run:
                        self.extract_zip(zip_file, temp_dir)
                    else:
                        print(f"[DRY-RUN] Would extract {zip_file} to {temp_dir}")
                # Find all .cue files in temp_dir
                cue_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith('.cue')]
                cue_files.sort()  # Ensure order
                if len(cue_files) == 0:
                    print(f"No .cue files found for {game_name}")
                    continue
                # If multi-disk, create m3u manifest
                if len(cue_files) > 1:
                    m3u_path = os.path.join(temp_dir, f"{game_name}.m3u")
                    m3u_contents = '\n'.join([os.path.basename(c) for c in cue_files])
                    if not dry_run:
                        with open(m3u_path, 'w') as m3u:
                            m3u.write(m3u_contents)
                    else:
                        print(f"[DRY-RUN] Would create m3u file: {m3u_path} with contents:\n{m3u_contents}")
                    input_arg = m3u_path
                else:
                    input_arg = cue_files[0]
                # Prepare output filename
                output_arg = os.path.join(self.source_dir, f"{game_name}.PBP")
                # Prepare command for psxpackager
                conversion = self.config.get('conversion', {})
                tool = conversion.get('tool', 'psxpackager')
                options = conversion.get('options', {})
                cmd = [tool, '-i', input_arg, '-o', output_arg]
                for k, v in options.items():
                    if isinstance(v, bool):
                        if v:
                            cmd.append(f'--{k}')
                    else:
                        cmd.append(f'--{k}')
                        cmd.append(str(v))
                if verbose or debug:
                    print(f"Running conversion command: {' '.join(cmd)}")
                if not dry_run:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        print("Conversion output:", result.stdout)
                        if result.stderr:
                            print("Conversion errors:", result.stderr)
                    except Exception as e:
                        print(f"Error running conversion tool: {e}")
                else:
                    print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
