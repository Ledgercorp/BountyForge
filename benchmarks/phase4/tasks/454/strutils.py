# Copyright (c) 2013, Mahmoud Hashemi
# Adapted excerpt from boltons 26.1.0; see ../LICENSE.upstream
import re
_find_sh_unsafe = re.compile(r'[^a-zA-Z0-9_@%+=:,./-]').search


def args2sh(args, sep=' '):
    """Return a shell-escaped string version of *args*, separated by
    *sep*, based on the rules of sh, bash, and other shells in the
    Linux/BSD/MacOS ecosystem.

    >>> print(args2sh(['aa', '[bb]', "cc'cc", 'dd"dd']))
    aa '[bb]' 'cc'"'"'cc' 'dd"dd'

    As you can see, arguments with no special characters are not
    escaped, arguments with special characters are quoted with single
    quotes, and single quotes themselves are quoted with double
    quotes. Double quotes are handled like any other special
    character.

    Based on code from the :mod:`pipes`/:mod:`shlex` modules. Also
    note that :mod:`shlex` and :mod:`argparse` have functions to split
    and parse strings escaped in this manner.
    """
    ret_list = []

    for arg in args:
        if not arg:
            ret_list.append("''")
            continue
        if _find_sh_unsafe(arg) is None:
            ret_list.append(arg)
            continue
        # use single quotes, and put single quotes into double quotes
        # the string $'b is then quoted as '$'"'"'b'
        ret_list.append("'" + arg.replace("'", "'\"'\"'") + "'")

    return ' '.join(ret_list)


def args2cmd(args, sep=' '):
    r"""Return a shell-escaped string version of *args*, separated by
    *sep*, using the same rules as the Microsoft C runtime.

    >>> print(args2cmd(['aa', '[bb]', "cc'cc", 'dd"dd']))
    aa [bb] cc'cc dd\"dd

    As you can see, escaping is through backslashing and not quoting,
    and double quotes are the only special character. See the comment
    in the code for more details. Based on internal code from the
    :mod:`subprocess` module.

    """
    # technique description from subprocess below
    """
    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.

    See http://msdn.microsoft.com/en-us/library/17w5ykft.aspx
    or search http://msdn.microsoft.com for
    "Parsing C++ Command-Line Arguments"
    """
    result = []
    needquote = False
    for arg in args:
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)