# 1G1R Deployment Tool

## About

I have a system in place using DAT files (XML based file archive comparison tools) that do a great job of sorting and
organizing emulation ROMS and disc images. These however, are not great tools for organizing ROMs and Games into
formats ready for EmulationStation. This script is supposed to cover that gap in my entertainment needs. It has the
ability of simply copying DAT-organized files into an destination directory, for simple formats like the Genesis or NES
systems. It also has the ability to convert an archived format (BIN/CUE or ISO) to a more common Disk Image format
like CHD or PBP.

## Usage

Install dependencies and run the CLI:

```sh
python -m src.onegame_onerom.cli --source <input_dir> --dest <dest_dir> --config ./config.yaml
```

## Configuration
See `config.yaml` for an example YAML config.
