Building HamCC
==============

In general, you should have a supported Python version installed already (currently >= 3.10).

Checkout the git repo

    # git clone git@github.com:gitandy/HamCC.git


Building on Linux
-----------------

Simply run

    # make build_devenv && make test

Now fire up your preferred Development tool, point your Python environment to the newly created venv and have fun.

Before running `make` again make sure to activate the venv.

    # source ./venv/bin/activate


Building on Windows
-------------------

First you should have installed a windows build of the GNU development tools.
I prefer a cygwin install with basic tools + make and git.

Start a CMD-Prompt or Powershell in your working copy and extend PATH to contain your python path

    # make.bat build_devenv
    # make.bat test

Now fire up your preferred Development tool, point your Python environment to the newly created venv and have fun.
