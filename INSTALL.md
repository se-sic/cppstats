# cppstats installation


## Overview

cppstats should be runnable under following systems:

* Linux/Ubuntu,
* Mac OS X, and
* Cygwin.

In detail, cppstats was successfully tested under:

- Ubuntu 12.04 64-bit, Python 2.7.3,
- Ubuntu 14.04 64-bit, Python 2.7.6, and
- Cygwin 64-bit, Python 2.7.3.

Right now, Python 3.x is NOT supported.

Current tested version of srcML:
`Trunk 19109c Thu May 22 09:18:31 2014 -0400`


## xUBUNTU

1. checkout repo

    ```bash
    git clone https://github.com/clhunsen/cppstats.git
    ```

2. install needed libraries (+ all dependencies)

    ```bash
    sudo apt-get install astyle  # artistic style (code formatter)
    sudo apt-get install xsltproc  # XSLT 1.0 command line processor
    sudo apt-get install libxml2 libxml2-dev  # library for processing XML
    sudo apt-get install gcc  # GNU compiler collection
    ```

    - download and install srcML libraries

        - download a binary package that is sufficient for you and your platform from: http://www.srcml.org/downloads.html
        - put the srcML binaries into your `$PATH` (so it can be called directly via "src2srcml" and "srcml2src")

        - if using 32-bit srcML libraries on an 64-bit platform

            ```bash
            sudo apt-get install ia32-libs  # 32bit compatibility libs (only on 64bit system needed)
            sudo apt-get install libarchive12:i386  # libarchive 32bit for linking with srcML libs (12.04)
            # or libarchive13:i386 if that one is current version (14.04)
            ```

        - if using an old srcML version on an up-to-date system

            - make soft links for updated libraries used by srcML, e.g.:

                ```bash
                sudo ln -s /usr/lib/i386-linux-gnu/libarchive.so.12 /usr/lib/i386-linux-gnu/libarchive.so.2
                ```

3. install Python package for cppstats and defined Python dependencies

    ```bash
    sudo python setup.py install
    ```
    
    Optionally, you can install it for the current user by appending `--user` to the command.
    
    If you want to install the package in *development mode*, substitute `install` with `develop`.
    
    Run `cppstats --help` for further instructions.

4. supply cppstats with the appropriate paths in `cppstats_input.txt`

    * use full paths like `/local/repos/mpsolve/mpsolve-2.2`
    * each project folder given in the file has to be structured as follows:

        ```
        > /local/repos/cpp-history/mpsolve/mpsolve-2.2/
            > source/ (here are the C source files)
        ```



CYGWIN
------

1. checkout repo

    ```bash
    git clone https://github.com/clhunsen/cppstats.git
    ```

    * **NOTE:** The old branch 'cygwin' is discontinued after version 0.8.
    * Git for Windows:
        * https://github.com/msysgit/msysgit/releases/
        * git bash only
        * checkout as-is, commit as-is

2. install needed libraries (+ all dependencies)

    - https://cygwin.com/install.html
        - install from internet
        - select any mirror
        - do not install any packages yet
        - wait setup for finish

    - **NOTE:** your Windows drives are located at `/cygdrive/`!

    - run following command within cygwin terminal:

        ```bash
        cygstart -- /path/to/cygwin-setup.exe -K http://cygwinports.org/ports.gpg
        ```

    - go through installation process as before, **but** add and select following download site:

        ```
        http://ftp-stud.fht-esslingen.de/pub/Mirrors/sourceware.org/cygwinports/
        ```

    - install following packages (version number, newer versions should
      also work, except for Python 3.x):

        ```
        - All/Python/
            python (2.7.3-1)
        - All/Libs/
            libxml2 (2.9.1-1)
            libxml2-devel (2.9.1-1)
            libxslt (1.1.27-2)
            libxslt-devel (1.1.27-2)
        - All/Utils/
            astyle (2.03-1)
        - All/Devel/
            gcc (4.7.3-1)
        + all dependencies you are prompted for
        ```

    - download and install srcML libraries
        - download a binary package that is sufficient for you and your Windows version from: http://www.srcml.org/lmcrs
        - extract into your `$PATH`, so that binaries are available directly
            - e.g., `C:/Program Files/Windows/system32/src2srcml.exe`

3. install Python package for cppstats and defined Python dependencies

    ```bash
    python setup.py develop --user
    ```

4. supply cppstats with the appropriate paths in `cppstats_input.txt`

    * use cygwin-paths like `/cygdrive/c/Users/user/data/mpsolve/mpsolve-2.2`
    * each project folder given in the file has to be structured as follows:

        ```
        > /cygdrive/c/Users/user/data/mpsolve/mpsolve-2.2
            > source/ (here are the C source files)
        ```
