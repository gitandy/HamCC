from cx_Freeze import setup, Executable
from hamcc import __copyright__

base = None

build_exe_options = {
    'packages': ['hamcc'],
    'excludes': ['tkinter',
                 'unittest',
                 ],
}

executables = [
    Executable('main.py',
               target_name='hamcc',
               base=base,
               copyright=__copyright__)
]

setup(options={
    'build_exe': build_exe_options,
},
    executables=executables)
