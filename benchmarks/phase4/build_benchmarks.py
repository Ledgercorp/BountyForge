"""Build attributed Boltons 26.1.0 excerpt fixtures, not complete upstream checkout."""
import json
from pathlib import Path
ROOT=Path(__file__).parent/'tasks'
SOURCE='https://github.com/mahmoud/boltons/tree/26.1.0'
S_STR='5df8cf6f2e067ce5a11691304f67faf6c2bac7cb'
S_CACHE='856bf195483aafbfcdb8f6f93a168daf0c9b5857'

BYTE_SOURCE='''_SIZE_SYMBOLS = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
_SIZE_BOUNDS = [(1024 ** i, sym) for i, sym in enumerate(_SIZE_SYMBOLS)]
_SIZE_RANGES = list(zip(_SIZE_BOUNDS, _SIZE_BOUNDS[1:]))


def bytes2human(nbytes, ndigits=0):
    """Turns an integer value of *nbytes* into a human readable format. Set
    *ndigits* to control how many digits after the decimal point
    should be shown (default ``0``).

    >>> bytes2human(128991)
    '126K'
    >>> bytes2human(100001221)
    '95M'
    >>> bytes2human(0, 2)
    '0.00B'
    >>> bytes2human(1024)
    '1K'
    """
    abs_bytes = abs(nbytes)
    for (size, symbol), (next_size, next_symbol) in _SIZE_RANGES:
        if abs_bytes < next_size:
            break
    hnbytes = float(nbytes) / size
    return '{hnbytes:.{ndigits}f}{symbol}'.format(hnbytes=hnbytes,
                                                  ndigits=ndigits,
                                                  symbol=symbol)
'''
LINE_SOURCE=r'''import re
_line_ending_re = re.compile(r'(\r\n|\n|\x0b|\f|\r|\x85|\x2028|\x2029)',
                             re.UNICODE)


def iter_splitlines(text):
    r"""Like :meth:`str.splitlines`, but returns an iterator of lines
    instead of a list. Also similar to :meth:`file.next`, as that also
    lazily reads and yields lines from a file.

    This function works with a variety of line endings, but as always,
    be careful when mixing line endings within a file.

    >>> list(iter_splitlines('\nhi\nbye\n'))
    ['', 'hi', 'bye', '']
    >>> list(iter_splitlines('\r\nhi\rbye\r\n'))
    ['', 'hi', 'bye', '']
    >>> list(iter_splitlines(''))
    []
    """
    prev_end, len_text = 0, len(text)
    # print('last: %r' % last_idx)
    # start, end = None, None
    for match in _line_ending_re.finditer(text):
        start, end = match.start(1), match.end(1)
        # print(start, end)
        if prev_end <= start:
            yield text[prev_end:start]
        if end == len_text:
            yield ''
        prev_end = end
    tail = text[prev_end:]
    if tail:
        yield tail
    return
'''
ARGS_SOURCE=r'''import re
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
'''
COUNT_SOURCE='''class ThresholdCounter:
    """Fixture shim: only iteritems and most_common from the upstream method."""
    def __init__(self, values):
        self.values = dict(values)

    def iteritems(self):
        return iter(self.values.items())

    def most_common(self, n=None):
        """Get the top *n* keys and counts as tuples. If *n* is omitted,
        returns all the pairs.
        """
        if not n or n <= 0:
            return []
        ret = sorted(self.iteritems(), key=lambda x: x[1], reverse=True)
        if n is None or n >= len(ret):
            return ret
        return ret[:n]
'''
CASES=[
 dict(id='454',issue='https://github.com/mahmoud/boltons/pull/454',file='strutils.py',source=ARGS_SOURCE, symbols=['args2sh','args2cmd'],description='The documented sep parameter is ignored. Both args2sh and args2cmd should join using the supplied custom separator while preserving quoting.',tests='''import unittest
from strutils import args2sh,args2cmd
class T(unittest.TestCase):
 def test_sh_separator(self): self.assertEqual(args2sh(['aa','bb'],sep='|'),'aa|bb')
 def test_cmd_separator(self): self.assertEqual(args2cmd(['aa','bb'],sep='|'),'aa|bb')
 def test_default(self): self.assertEqual(args2sh(['aa','bb']),'aa bb')
 def test_cmd_default(self): self.assertEqual(args2cmd(['aa','bb']),'aa bb')
''',blob=S_STR),
 dict(id='459',issue='https://github.com/mahmoud/boltons/pull/459',file='strutils.py',source=BYTE_SOURCE,symbols=['bytes2human'],description="The largest yottabyte (Y) unit is unreachable; bytes2human(1024**8) should return '1Y' and 5 times that should produce '5Y' without changing smaller units.",tests='''import unittest
from strutils import bytes2human
class T(unittest.TestCase):
 def test_yotta(self): self.assertEqual(bytes2human(1024**8),'1Y')
 def test_five_yotta(self): self.assertEqual(bytes2human(5*1024**8),'5Y')
 def test_zetta(self): self.assertEqual(bytes2human(1024**7),'1Z')
''',blob=S_STR),
 dict(id='475',issue='https://github.com/mahmoud/boltons/pull/475',file='strutils.py',source=LINE_SOURCE,symbols=['iter_splitlines'],description='iter_splitlines should split U+2028 and U+2029 Unicode separators. Ordinary text containing 28 or 29 must not be split accidentally.',tests='''import unittest
from strutils import iter_splitlines
class T(unittest.TestCase):
 def test_unicode(self): self.assertEqual(list(iter_splitlines('A\\u2028B\\u2029C')),['A','B','C'])
 def test_regular_date(self): self.assertEqual(list(iter_splitlines('February 28, 2026')),['February 28, 2026'])
 def test_newline(self): self.assertEqual(list(iter_splitlines('A\\nB')),['A','B'])
''',blob=S_STR),
 dict(id='460',issue='https://github.com/mahmoud/boltons/pull/460',file='cacheutils.py',source=COUNT_SOURCE,symbols=['most_common'],description='ThresholdCounter.most_common() with no n argument unexpectedly returns an empty list rather than all pairs sorted descending. Explicit n=0 and negative values still return empty.',tests='''import unittest
from cacheutils import ThresholdCounter
class T(unittest.TestCase):
 def test_omitted(self): self.assertEqual(ThresholdCounter({'a':2,'b':4}).most_common(),[('b',4),('a',2)])
 def test_zero(self): self.assertEqual(ThresholdCounter({'a':2}).most_common(0),[])
 def test_one(self): self.assertEqual(ThresholdCounter({'a':2,'b':4}).most_common(1),[('b',4)])
''',blob=S_CACHE),
 dict(id='524',issue='https://github.com/mahmoud/boltons/issues/524',file='strutils.py',source=BYTE_SOURCE,symbols=['bytes2human'],description="When the number rounds to 1024 in the current unit, promote to the next unit: bytes2human(1048575) -> '1M', (1023.5) -> '1K', (1023.99,1) -> '1.0K'.",tests='''import unittest
from strutils import bytes2human
class T(unittest.TestCase):
 def test_rounded_megabyte(self): self.assertEqual(bytes2human(1048575),'1M')
 def test_rounded_kib(self): self.assertEqual(bytes2human(1023.5),'1K')
 def test_rounded_one_digit(self): self.assertEqual(bytes2human(1023.99,1),'1.0K')
 def test_existing(self): self.assertEqual(bytes2human(1024),'1K')
''',blob=S_STR)
]
index=[]
for x in CASES:
 p=ROOT/x['id'];(p/'tests').mkdir(parents=True,exist_ok=True)
 (p/x['file']).write_text('# Copyright (c) 2013, Mahmoud Hashemi\n# Adapted excerpt from boltons 26.1.0; see ../LICENSE.upstream\n'+x['source'],encoding='utf-8')
 (p/'tests/test_regression.py').write_text(x['tests'],encoding='utf-8')
 index.append({k:x[k] for k in ('id','issue','file','symbols','description','blob')})
index=sorted(index,key=lambda x:x['id'])
(ROOT/'manifest.json').write_text(json.dumps({'project':'boltons','historical_tag':'26.1.0','upstream_repo':SOURCE,'verification_scope':'curated upstream-derived excerpts with deterministic tests, not full upstream repository','tasks':index},indent=2)+'\n')
print('wrote',len(CASES),'historical issue fixtures')