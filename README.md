# 1G1R Scripts

### About

This is a collection of scripts I use to organize my ROMs and Games for EmulationStation. Instead of being entirely
separate, I've thrown many of them together into a single collection, as there can often be some overlap.

### Development

Add a new command to `onegame_onerom/commands/` with the filename `cmd_something.py` and it should automatically be
as:
```bash
python -m onegame_onerom something
```

### Scripts and Usage

#### Backups/Restore


Stupidly simple script to backup and restore specific filetypes from some source root. The configuration attempts to
specify which filetypes to backup and restore for each system directory, (eg. `nes` for NES games and `*.srm` for a
filetype). Theres an additional __restore__ script that will revert the backup files to their original location.


##### Usage

Backup:

```bash 
python -m onegame_onerom backup ./config.yaml --threads=32
```

Restore:

```bash
python -m onegame_onerom restore --threads=32 ./config.yaml
```

#### Systems

I have a system in place with RomVault using DAT files (XML based file archive comparison tools) that do a great job of
sorting and organizing emulation ROMS and disc images. These however, are not great tools for organizing ROMs and Games
into formats ready for EmulationStation. This script is supposed to cover that gap in my entertainment needs. It has the
ability of simply copying DAT-organized files into an destination directory, for simple formats like the Genesis or NES
systems. It also has the ability to convert an archived format (BIN/CUE or ISO) to a more common Disk Image format
like CHD or PBP.

Note that this isn't that fast. There is a little bit of concurrency in the Copy-Only processor, but everything else is
single threaded. 

##### Usage

Install dependencies and run the CLI:

```sh
python -m onegame_onerom convert --verbose ./config.yaml
```

### Configuration
See `config.yaml` for an example YAML config.
