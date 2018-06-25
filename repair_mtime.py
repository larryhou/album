#!/usr/bin/env python3
import argparse, sys, os, io, time, re

def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--asset-path', '-p', required=True)
    options = arguments.parse_args(sys.argv[1:])
    asset_path = options.asset_path
    assert os.path.exists(asset_path)
    process = os.popen('exiftool -stay_open True -r -e -n -createdate {}'.format(asset_path))
    buffer = io.StringIO(process.read())
    process.close()
    while True:
        line = buffer.readline() # type: str
        if not line: break
        if line.startswith('===='):
            file_path = line[9:-1]
            if not re.search(r'\.(MP4|JPG|MOV)$', file_path, re.IGNORECASE): continue
            data_line = buffer.readline() # type: str
            if not data_line: continue
            create_date = time.strptime(data_line[-20:-1], '%Y:%m:%d %H:%M:%S')
            create_time = int(time.mktime(create_date))
            os.utime(file_path, (create_time, create_time))
            print('{} => {}'.format(file_path, time.strftime('%Y-%m-%dT%H:%M:%S', create_date)))

if __name__ == '__main__':
    main()