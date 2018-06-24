#!/usr/bin/env python3

import argparse, os, sys, hashlib, re, time, json, tempfile

DATABASE_FIELD_NAME_INDEX = 'index'
DATABASE_FIELD_NAME_HASH = 'hash'
DATABASE_STORAGE_NAME = 'database.json'

class script_commands(object):
    seperate_database = 'seperate-database'
    import_project    = 'import-project'
    import_assets     = 'import-assets'

    @classmethod
    def get_option_choices(cls):
        choice_list = []
        for name, value in vars(cls).items():
            if name.replace('_', '-') == value: choice_list.append(value)
        return choice_list

class ArgumentOptions(object):
    def __init__(self, data):
        self.import_path = data.import_path # type: str
        self.work_path = data.work_path # type: str
        self.hash_size = data.hash_size # type: str
        self.file_types = data.file_type # type: list
        self.project_name = data.project_name # type: str
        self.project_path = data.project_path # type: str
        self.command = data.command # type: str
        self.with_copy = data.with_copy # type: bool

def import_assets(options:ArgumentOptions):
    pattern = re.compile(r'\.(JPG|MOV|MP4)$', re.IGNORECASE)
    if options.file_types:
        pattern = re.compile(r'\.(%s)$' % ('|'.join(options.file_types)), re.IGNORECASE)

    project_path = os.path.join(options.work_path, options.project_name)
    if not os.path.exists(project_path):
        os.makedirs(project_path)

    database = {} # type: dict[str,dict]
    def get_database(name:str, reload_from_disk = False)->dict:
        if name in database and not reload_from_disk:
            return database[name]
        database_path = os.path.join(project_path, name)
        data = {}
        if os.path.exists(database_path):
            try:
                with open(database_path, 'r+') as fp:
                    data = json.load(fp)
            except _: pass
        for field_name in [DATABASE_FIELD_NAME_HASH, DATABASE_FIELD_NAME_INDEX]:
            if field_name not in data: data[field_name] = {}
        database[name] = data
        return data

    md5 = hashlib.md5()
    hash_size = int(options.hash_size)
    # generate incremental list
    increment_list = []
    for walk_path, _, file_name_list in os.walk(options.import_path):
        for file_name in file_name_list:
            target_location = os.path.join(walk_path, file_name)
            if not pattern.search(file_name) or os.path.islink(target_location): continue
            timestamp = os.stat(target_location).st_birthtime
            mtime = time.localtime(os.path.getmtime(target_location))
            hash_map = get_database(name=str(mtime.tm_year)).get(DATABASE_FIELD_NAME_HASH)
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
        index_map = get_database(name=str(mtime.tm_year)).get(DATABASE_FIELD_NAME_INDEX)
        if label not in index_map: index_map[label] = 1
        common_path = src_location[:-4]
        sequence = live_map.get(common_path)
        if sequence is None:
            sequence = index_map.get(label)
            live_map[common_path] = sequence
            index_map[label] += 1
        file_name = '%s_%04d%s' % (label, sequence, src_location[-4:])
        dst_group_location = '%s/%04d' % (project_path, mtime.tm_year)
        if not os.path.exists(dst_group_location):
            os.makedirs(dst_group_location)
        dst_location = '%s/%s' % (dst_group_location, file_name)
        assert not os.path.exists(dst_location)
        hash_map[digest] = file_name
        if not options.with_copy:
            bash_script.write('mv -v \'%s\' \'%s\'\n' % (src_location, dst_location))
        else:
            bash_script.write('cp -v \'%s\' \'%s\'\n' % (src_location, dst_location))
        print(digest, '%s => %s' % (src_location, dst_location))
    bash_script.write('rm -f %s\n' % bash_script.name)
    # bash_script.seek(0)
    # print bash_script.read()
    bash_script.close()
    os.system('bash -e %s' % bash_script.name)

    for name, mini_database in database.items():
        write_database(mini_database, project_path=os.path.join(project_path, name))

def seperate_database(options:ArgumentOptions):
    database = json.load(open('{}/{}'.format(options.project_path, DATABASE_STORAGE_NAME), 'r+'))
    index_map = database.get(DATABASE_FIELD_NAME_INDEX) # type: dict
    assert index_map
    group_index_map = {} # type: dict[str:tuple[str, str]]
    for name, value in index_map.items():
        year = name[:4]
        if year not in group_index_map: group_index_map[year] = []
        group_index_map[year].append((name, value))
    hash_map = database.get(DATABASE_FIELD_NAME_HASH) # type: dict
    assert hash_map
    group_hash_map = {} # type: dict[str:tuple[str, str]]
    for hash, name in hash_map.items():
        year = name[:4]
        if year not in group_hash_map: group_hash_map[year] = []
        group_hash_map[year].append((hash, name))
    assert group_hash_map.keys() == group_index_map.keys()
    for year in group_index_map.keys():
        mini_project_path = os.path.join(options.project_path, year)
        assert os.path.exists(mini_project_path)
        mini_database = {}
        index_map = mini_database[DATABASE_FIELD_NAME_INDEX] = {}
        for key, value in group_index_map.get(year): index_map[key] = value
        hash_map = mini_database[DATABASE_FIELD_NAME_HASH] = {}
        for key, value in group_hash_map.get(year): hash_map[key] = value
        write_database(mini_database, project_path=mini_project_path)

def write_database(data:dict, project_path:str):
    database_path = os.path.join(project_path, DATABASE_STORAGE_NAME)
    with open(database_path, 'w+') as fp:
        json.dump(data, fp, indent=4)
        fp.close()
        print('database => {}'.format(database_path))

def import_project(options:ArgumentOptions):
    pass


def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--command', '-c', default=script_commands.import_assets, choices=script_commands.get_option_choices())
    arguments.add_argument('--import-path', '-i', help='local folder path for walking through to import')
    arguments.add_argument('--work-path', '-w', default=os.path.expanduser('/Volumes/Remember/CameraRoll'), help='local folder path for moveing to')
    arguments.add_argument('--hash-size', '-s', type=int, default=1024*10, help='num of bytes for md5sum caculation')
    arguments.add_argument('--file-type', '-t', nargs='+', help='file extension types for keep-filter')
    arguments.add_argument('--project-name', '-n', help='album project name')
    arguments.add_argument('--project-path', '-p')
    arguments.add_argument('--with-copy', action='store_true')
    options = ArgumentOptions(data=arguments.parse_args(sys.argv[1:]))

    if options.command == script_commands.import_assets:
        assert options.import_path and os.path.exists(options.import_path)
        assert options.work_path and os.path.exists(options.work_path)
        assert options.hash_size >= 1024
        assert options.project_name
        import_assets(options)
    elif options.command == script_commands.seperate_database:
        assert options.project_path and os.path.exists(options.project_path)
        seperate_database(options)
    elif options.command == script_commands.import_project:
        assert options.project_path and os.path.exists(options.project_path)
        assert options.project_name
        import_project(options)

if __name__ == '__main__':
    main()