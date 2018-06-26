#!/usr/bin/env python3
import argparse, sys
import album_arrange

def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--asset-path', '-p', required=True)
    options = arguments.parse_args(sys.argv[1:])
    album_arrange.repair_asset_times(asset_path=options.asset_path)

if __name__ == '__main__':
    main()