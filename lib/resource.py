'''
Licensed under MIT
Copyright (c) 2015 r3a1ay <https://github.com/r3a1ay>
'''

import errno
import os
import sublime
import traceback


def resource(package_name, filename, data=None):
    packages_parent_path = os.path.abspath(sublime.packages_path() + '/..')
    res_paths, res_files = resource_paths(package_name, filename)

    # read
    if data is None:
        if int(sublime.version()) >= 3000:
            for rf in res_files:
                try:
                    data = sublime.load_resource(
                        os.path.relpath(rf, packages_parent_path))
                    break
                except:
                    print(traceback.print_exc())
                    pass
        else:
            for rf in res_files:
                try:
                    f = open(rf, 'r')
                    data = f.read()
                    f.close()
                    break
                except:
                    print(traceback.print_exc())
                    pass
        return data

    # write
    res_path = res_paths[0]
    res_file = res_files[0]
    if not os.path.exists(res_path):
        try:
            os.makedirs(res_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                print(traceback.print_exc())
                return None
    try:
        f = open(res_file, 'w')
        f.write(data)
        f.close()
        return data
    except:
        print(traceback.print_exc())
        pass

    return None


def resource_paths(package_name, filename):
    res_paths = (
        os.path.join(sublime.packages_path(), 'User', package_name),
        os.path.join(sublime.packages_path(), package_name))
    res_files = (
        os.path.join(res_paths[0], filename),
        os.path.join(res_paths[1], filename))
    return (res_paths, res_files)
