#!/usr/bin/env python3

import argparse, os, sys, hashlib, re, time, json, tempfile

DB_FIELD_NAME_HASH = 'hash'
DB_FIELD_NAME_INDX = 'index'

def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--import-path', '-i', required=True, help='local folder path for walking through to import')
    arguments.add_argument('--work-path', '-w', default=os.path.expanduser('~/Pictures/AlbumArrange'), help='local folder path for moveing to')
    arguments.add_argument('--hash-size', '-s', default=1024*10, help='num of bytes for md5sum caculation')
    arguments.add_argument('--file-type', '-t', nargs='+', help='file extension types for keep-filter')
    arguments.add_argument('--project', '-p', required=True, help='album project name')
    data = arguments.parse_args(sys.argv[1:])

    pattern = re.compile(r'\.(JPG|MOV|MP4)$', re.IGNORECASE)
    if data.file_type:
        type_list = data.file_type
        pattern = re.compile(r'\.(%s)$'%('|'.join(type_list)), re.IGNORECASE)

    import_path = data.import_path
    assert os.path.exists(import_path)

    proj_path = os.path.join(data.work_path, data.project)
    if not os.path.exists(proj_path):
        os.makedirs(proj_path)

    database = {}
    database_location = os.path.join(proj_path, 'database.json')
    if os.path.exists(database_location):
        try:
            with open(database_location, 'r+') as fp:
                database = json.load(fp)
        except: pass

    for field_name in [DB_FIELD_NAME_HASH, DB_FIELD_NAME_INDX]:
        if field_name not in database: database[field_name] = {}

    hash_map = database.get(DB_FIELD_NAME_HASH)
    indx_map = database.get(DB_FIELD_NAME_INDX)

    md5 = hashlib.md5()
    hash_size = int(data.hash_size)
    # generate incremental list
    increment_list = []
    for walk_path,_, file_name_list in os.walk(import_path):
        for file_name in file_name_list:
            target_location = os.path.join(walk_path, file_name)
            if not pattern.search(file_name) or os.path.islink(target_location): continue
            timestamp = os.stat(target_location).st_birthtime
            mtime = time.localtime(os.path.getmtime(target_location))
            with open(target_location, 'r+b') as fp:
                md5.update(fp.read(hash_size))
                digest = md5.hexdigest()
                fp.close()
                if digest in hash_map: continue
                item = (timestamp, mtime, digest, target_location)
                increment_list.append(item)
    def camera_roll_sort(a, b):
        if a[0] != b[0]: return 1 if a[0] > b[0] else -1
        return 1 if a[-1] > b[-1] else -1
    from functools import cmp_to_key
    increment_list.sort(key=cmp_to_key(camera_roll_sort))
    # generate image move path
    live_map = {}
    bash_script = open(tempfile.mktemp('-AlbumArrange.sh'), 'w+')
    bash_script.write('#!/usr/bin/env bash\n')
    for n in range(len(increment_list)):
        _, mtime, digest, src_location = increment_list[n]
        label = '%02d%02d' % (mtime.tm_year, mtime.tm_mon)
        if label not in indx_map: indx_map[label] = 1
        common_path = src_location[:-4]
        sequence = live_map.get(common_path)
        if sequence is None:
            sequence = indx_map.get(label)
            live_map[common_path] = sequence
            indx_map[label] += 1
        file_name = '%s_%04d%s' % (label, sequence, src_location[-4:])
        dst_group_location = '%s/%04d'%(proj_path, mtime.tm_year)
        if not os.path.exists(dst_group_location):
            os.makedirs(dst_group_location)
        dst_location = '%s/%s'%(dst_group_location, file_name)
        assert not os.path.exists(dst_location)
        hash_map[digest] = file_name
        bash_script.write('mv -v \'%s\' \'%s\'\n'%(src_location, dst_location))
        print(digest, '%s => %s'%(src_location, dst_location))
    bash_script.write('rm -f %s\n'%bash_script.name)
    # bash_script.seek(0)
    # print bash_script.read()
    bash_script.close()
    os.system('bash -e %s'%bash_script.name)

    with open(database_location, 'w+') as fp:
        json.dump(database, fp, indent=4)
        fp.close()



if __name__ == '__main__':
    main()