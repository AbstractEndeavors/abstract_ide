from __future__ import annotations
import re
from abstract_utilities import *
from typing import List, Dict, Any, Tuple
from PyQt6.QtWidgets import QStackedWidget, QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QLabel,QTreeWidget, QTreeWidgetItem, QHeaderView, QButtonGroup

# Return:
# {
#   'entries': [ { 'path', 'line', 'col', 'severity', 'code', 'message' }, ... ],
#   'errors':  [...subset...],
#   'warnings':[...subset...],
# }
ERROR_PHRASES   = ['does not','cannot','has no','must be']
WARNING_PHRASES = ['is declared']

DEMOTE_CODES = {'TS6133'}  # treat these as warnings
def _compile_phrase_rx(phrases):
    phrases = [p.strip() for p in phrases or [] if p.strip()]
    if not phrases:
        return None
    # case-insensitive, word-ish boundaries; escape phrases safely
    pat = r'(?i)(?<!\w)(?:' + '|'.join(re.escape(p) for p in phrases) + r')(?!\w)'
    return re.compile(pat)

_ERR_RX = _compile_phrase_rx(ERROR_PHRASES)
_WRN_RX = _compile_phrase_rx(WARNING_PHRASES)
def get_tripple_string(string):
    nustring = ''
    for i in range(3):
        nustring +=string
    return nustring
def get_within_quotes(text,quotes=None):
    quotes_strings = quotes or ["'",'"']
    in_quotes = []
    for quotes_string in quotes_strings:
        if not isinstance(quotes_string,list):
            tripple= get_tripple_string(quotes_string)
            texts = [text]
            if tripple in text:
                texts= text.split(tripple)
            for text_part in texts:
                quote_count = len(text_part) - len(text_part.replace(quotes_string,''))
                quote_spl = text_part.split(quotes_string)
                in_quotes+=[quote_spl[i] for i in range(quote_count) if ((i == 1 or i%2 != float(0)) and len(quote_spl) > i)]
        else:
            texts= text.split(quotes_string[0])
            for text in texts:
                in_quotes.append(text.split(quotes_string[1])[0])
    return in_quotes

def _phrase_hit(msg, rx):
    return bool(rx.search(msg)) if (rx and msg) else False
def parse_tsc_output(
    text: str,
    *,
    error_phrases: list[str] = None,
    warning_phrases: list[str] = None,
    require_phrase_match: bool = False,
    escalate_warning_on_error_phrase: bool = True,
    demote_error_on_warning_phrase: bool = True,      # NEW
    demote_codes: set[str] = DEMOTE_CODES,            # NEW
) -> Dict[str, Any]:
    if not text:
        return {'entries': [], 'errors': [], 'warnings': []}

    # (allow caller to override)
    err_rx = _compile_phrase_rx(error_phrases) if error_phrases is not None else _ERR_RX
    wrn_rx = _compile_phrase_rx(warning_phrases) if warning_phrases is not None else _WRN_RX

    pat1 = re.compile(r"""^(?P<path>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s+
                          (?P<severity>error|warning)\s+
                          (?P<code>TS\d+)\s*:\s*(?P<msg>.+)$""",
                      re.IGNORECASE | re.VERBOSE)
    pat2 = re.compile(r"""^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+)\s*-\s*
                          (?P<severity>error|warning)\s+
                          (?P<code>TS\d+)\s*:\s*(?P<msg>.+)$""",
                      re.IGNORECASE | re.VERBOSE)
    pat3_head = re.compile(r"^(?P<severity>error|warning)\s*:\s*(?P<msg>.+)$", re.IGNORECASE)
    pat3_loc  = re.compile(r"^\s*at\s+(?P<path>.+?):(?P<line>\d+):(?P<col>\d+)\s*:?\s*$", re.IGNORECASE)

    entries = []
    pending = None
    for line in text.splitlines():
        m = pat1.match(line) or pat2.match(line)
        if m:
            d = m.groupdict()
            msg = d['msg']
            sev = d['severity'].lower()
            code = d['code']  # like 'TS6133'
            
            hit_err = _phrase_hit(msg, err_rx)
            hit_wrn = _phrase_hit(msg, wrn_rx)

            # demote certain "errors" to warnings
            if demote_error_on_warning_phrase and sev == 'error':
                if hit_wrn or (code and code in (demote_codes or set())):
                    sev = 'warning'

            # optional escalation (warnings that look like real errors)
            if escalate_warning_on_error_phrase and sev == 'warning' and hit_err:
                sev = 'error'

            # optional filter: require a phrase hit in the corresponding list
            if require_phrase_match:
                ok = (sev == 'error'   and (hit_err or not err_rx)) or \
                     (sev == 'warning' and (hit_wrn or not wrn_rx))
                if not ok:
                    continue

            entries.append({
                'path': d['path'],
                'line': int(d['line']),
                'col':  int(d['col']),
                'severity': sev,
                'code': code,
                'msg': msg,
                'vars': get_within_quotes(line),
                'hit_error_phrase': hit_err,
                'hit_warning_phrase': hit_wrn,
            })
            pending = None
            continue

        # Vite/esbuild two-line format
        m = pat3_head.match(line)
        if m:
            pending = {'severity': m.group('severity').lower(), 'msg': m.group('msg')}
            continue
        if pending:
            m = pat3_loc.match(line)
            if m:
                msg = pending['msg']
                sev = pending['severity']
                hit_err = _phrase_hit(msg, err_rx)
                hit_wrn = _phrase_hit(msg, wrn_rx)
                # no code in this format; phrase only
                if demote_error_on_warning_phrase and sev == 'error' and hit_wrn:
                    sev = 'warning'
                if escalate_warning_on_error_phrase and sev == 'warning' and hit_err:
                    sev = 'error'
                if require_phrase_match:
                    ok = (sev == 'error'   and (hit_err or not err_rx)) or \
                         (sev == 'warning' and (hit_wrn or not wrn_rx))
                    if not ok:
                        pending = None
                        continue

                entries.append({
                    'path': m.group('path'),
                    'line': int(m.group('line')),
                    'col':  int(m.group('col')),
                    'severity': sev,
                    'code': None,
                    'msg': msg,
                    'vars': get_within_quotes(line),
                    'hit_error_phrase': hit_err,
                    'hit_warning_phrase': hit_wrn,
                })
                pending = None

    errors   = [e for e in entries if e['severity'] == 'error']
    warnings = [e for e in entries if e['severity'] == 'warning']
    return {'entries': entries, 'errors': errors, 'warnings': warnings}

def get_error_type(e):
    is_error = False
    is_warning = False
    if e['severity'] == 'error':
        is_error = True
    elif e['severity'] == 'warning':
        is_warning = True
    return is_error,is_warning
def get_errors(e,
               only_errors=None,
               only_warnings=None,
               require_error_phrase=False,
               require_warning_phrase=False
               ):
    is_error,is_warning = get_error_type(e)
    if is_error == True:
        if require_error_phrase and not e['hit_error_phrase']:
            return 
        if only_errors == True or (only_errors == None and only_warnings == None):
            return e

    if is_warning == True:
        if require_warning_phrase and not e['hit_warning_phrase']:
            return 
        if only_warnings == True or (only_errors == None and only_warnings == None):
            return e
def filter_entries(entries,
                   *,
                   only_errors=None,     # True/False/None
                   only_warnings=None,     # True/False/None
                   require_error_phrase=False,
                   require_warning_phrase=False):
    out = []
    for e in entries:
        e = get_errors(e,
               only_errors=only_errors,
               only_warnings=only_warnings,
               require_error_phrase=require_error_phrase,
               require_warning_phrase=require_warning_phrase
              ) 
           
        if e:
            out.append(e)
    return out
def format_entry_for_log(e: dict) -> str:
    code = f" {e['code']}" if e.get('code') else ""
    # use 'msg' (that’s what you saved) not 'message'
    return f"{e['severity'].upper()}{code}: {e['path']}:{e['line']}:{e['col']} — {e.get('msg','')}"


def get_entry_output(last_output: str):
    last_output = last_output or ""
    # parse & split to errors/warnings for filtering and lists
    # parse & split to errors/warnings for filtering and lists
    res = parse_tsc_output(last_output)
    parsed_entries = res.get('entries')
    res["errors"] = filter_entries(parsed_entries, only_errors=True, require_error_phrase=False)
    res["warnings"] = filter_entries(parsed_entries, only_warnings=True, require_warning_phrase=False)
    res["all"] = res["errors"]+res["warnings"]

    res["errors_only"]   = "\n".join(format_entry_for_log(e) for e in res["errors"])
    res["warnings_only"] = "\n".join(format_entry_for_log(e) for e in res["warnings"])
    res["all_only"] = "\n".join(format_entry_for_log(e) for e in res["all"])
    # refresh visible lists
    res["error_entries"] = [(e.get('path',''), e.get('line',''), e.get('col',''), e.get('msg',''), e.get('code',''), e.get('vars','')) for e in res["errors"]]
    res["warning_entries"] = [(e.get('path',''), e.get('line',''), e.get('col',''), e.get('msg',''), e.get('code',''), e.get('vars','')) for e in res["warnings"]]
    res["all_entries"]= res["error_entries"]+res["warning_entries"]
    return res
get_errors= """error TS5033: Could not write file '/var/www/html/thedialydialectics/tsconfig.tsbuildinfo': EACCES: permission denied, open '/var/www/html/thedialydialectics/tsconfig.tsbuildinfo'.

src/components/Body/Body.tsx:3:25 - error TS2307: Cannot find module '@PdfViewer' or its corresponding type declarations.

3 import  PdfViewer  from '@PdfViewer';
                          ~~~~~~~~~~~~

src/components/MetaData/Head/meta_image.tsx:21:11 - error TS6133: 'baseUrl' is declared but its value is never read.

21     const baseUrl = schema?.url || socialMeta['og:image'];
             ~~~~~~~

src/components/Navbar/Navbar.tsx:2:18 - error TS2307: Cannot find module 'next/link' or its corresponding type declarations.

2 import Link from 'next/link';
                   ~~~~~~~~~~~

src/components/Navbar/Navbar.tsx:3:29 - error TS2307: Cannot find module 'next/navigation' or its corresponding type declarations.

3 import { usePathname } from 'next/navigation';
                              ~~~~~~~~~~~~~~~~~

src/components/Navbar/Navbars.tsx:3:1 - error TS6133: 'Link' is declared but its value is never read.

3 import Link from 'next/link';
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/components/Navbar/Navbars.tsx:3:18 - error TS2307: Cannot find module 'next/link' or its corresponding type declarations.

3 import Link from 'next/link';
                   ~~~~~~~~~~~

src/components/Navbar/Navbars.tsx:4:29 - error TS2307: Cannot find module 'next/navigation' or its corresponding type declarations.

4 import { usePathname } from 'next/navigation';
                              ~~~~~~~~~~~~~~~~~

src/components/Navbar/Navbars.tsx:12:54 - error TS6133: 'theme' is declared but its value is never read.

12 const Navbar: React.FC<NavbarProps> = ({ links = [], theme }) => {
                                                        ~~~~~

src/components/Navbar/Navbars.tsx:39:41 - error TS6133: 'index' is declared but its value is never read.

39             links.map(({ href, label }, index) => (
                                           ~~~~~

src/components/PageHeader/PageHeader.tsx:1:19 - error TS2307: Cannot find module 'next/image' or its corresponding type declarations.

1 import Image from 'next/image';
                    ~~~~~~~~~~~~

src/components/Social/Props/ShareButton.tsx:2:10 - error TS2724: '"@interfaces"' has no exported member named 'SocialShareUrlButtonProps'. Did you mean 'SocialShareButtonProps'?

2 import { SocialShareUrlButtonProps } from '@interfaces';
           ~~~~~~~~~~~~~~~~~~~~~~~~~

src/components/Social/Props/ShareButton.tsx:11:3 - error TS2339: Property 'platform' does not exist on type 'ShareButtonProps'.

11   platform = 'x',
     ~~~~~~~~

src/components/Social/Props/ShareButton.tsx:12:3 - error TS2339: Property 'text' does not exist on type 'ShareButtonProps'.

12   text = '',
     ~~~~

src/components/Social/Props/ShareButton.tsx:13:3 - error TS2339: Property 'url' does not exist on type 'ShareButtonProps'.

13   url = '',
     ~~~

src/components/Social/Props/ShareButton.tsx:14:3 - error TS2339: Property 'via' does not exist on type 'ShareButtonProps'.

14   via = '',
     ~~~

src/components/Social/Props/ShareButton.tsx:15:3 - error TS2339: Property 'hashtags' does not exist on type 'ShareButtonProps'.

15   hashtags = '',
     ~~~~~~~~

src/components/Social/Props/ShareButton.tsx:42:13 - error TS2322: Type '{ key: string; platform: string; text: any; url: any; via: any; hashtags: any; }' is not assignable to type 'IntrinsicAttributes & ShareButtonProps'.
  Property 'platform' does not exist on type 'IntrinsicAttributes & ShareButtonProps'.

42             platform={platform}
               ~~~~~~~~

src/components/Social/Props/ShareButton.tsx:54:13 - error TS2322: Type '{ key: string; platform: string; text: any; url: any; via: any; hashtags: any; }' is not assignable to type 'IntrinsicAttributes & ShareButtonProps'.
  Property 'platform' does not exist on type 'IntrinsicAttributes & ShareButtonProps'.

54             platform={platform}
               ~~~~~~~~

src/components/SourceEditor/SourceEditor.tsx:20:11 - error TS6196: 'MetadataEditorProps' is declared but never used.

20 interface MetadataEditorProps {
             ~~~~~~~~~~~~~~~~~~~

src/components/pdfViewer/pdfViewer.tsx:4:19 - error TS2307: Cannot find module 'next/image' or its corresponding type declarations.

4 import Image from 'next/image';
                    ~~~~~~~~~~~~

src/functions/content_parser.tsx:3:1 - error TS6192: All imports in import declaration are unused.

3 import {url_to_path,path_to_url,get_full_path,get_full_url} from './tdd_path_utils';
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/functions/content_parser.tsx:75:38 - error TS6133: 'meta' is declared but its value is never read.

75 export function iframeIt(content:any,meta?:any, filename?:any){
                                        ~~~~

src/functions/content_parser.tsx:75:49 - error TS6133: 'filename' is declared but its value is never read.

75 export function iframeIt(content:any,meta?:any, filename?:any){
                                                   ~~~~~~~~

src/functions/content_parser.tsx:99:38 - error TS6133: 'meta' is declared but its value is never read.

99 export function lyricsIt(content:any,meta?:any, filename?:any){
                                        ~~~~

src/functions/content_parser.tsx:99:49 - error TS6133: 'filename' is declared but its value is never read.

99 export function lyricsIt(content:any,meta?:any, filename?:any){
                                                   ~~~~~~~~

src/functions/content_parser.tsx:112:45 - error TS6133: 'filename' is declared but its value is never read.

112 export function imgIt(content:any,meta:any, filename?:any){
                                                ~~~~~~~~

src/functions/content_parser.tsx:115:39 - error TS6133: 'jsonPath' is declared but its value is never read.

115         (_: string, filename: string, jsonPath: string, width: string | undefined, height: string | undefined) => {
                                          ~~~~~~~~

src/functions/content_parser.tsx:152:21 - error TS6133: 'directory' is declared but its value is never read.

152         (_: string, directory: string, width?: string, height?: string, background?: string) => {
                        ~~~~~~~~~

src/functions/content_parser.tsx:152:73 - error TS6133: 'background' is declared but its value is never read.

152         (_: string, directory: string, width?: string, height?: string, background?: string) => {
                                                                            ~~~~~~~~~~

src/functions/content_parser.tsx:233:54 - error TS6133: 'filename' is declared but its value is never read.

233 export async function seoImgIt(content:any,meta:any, filename?:any){
                                                         ~~~~~~~~

src/functions/content_parser.tsx:270:19 - error TS6133: 'style' is declared but its value is never read.

270             const style="background-color: ${background || 'white'}; max-width: 100%; height: auto;"
                      ~~~~~

src/functions/content_parser.tsx:271:19 - error TS6133: 'loading' is declared but its value is never read.

271             const loading="lazy"
                      ~~~~~~~

src/functions/index.ts:2:1 - error TS2308: Module './content_parser' has already exported a member named 'build_content'. Consider explicitly re-exporting to resolve the ambiguity.

2 export * from './functions.server';
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/functions/index.ts:4:1 - error TS2308: Module './functions.server' has already exported a member named 'get_filename'. Consider explicitly re-exporting to resolve the ambiguity.

4 export * from './path_utils_client';
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/functions/path_utils_client.ts:3:49 - error TS2307: Cannot find module '@putkoff/abstract-utilities' or its corresponding type declarations.

3 import { ensure_list, eatOuter, eatInner } from '@putkoff/abstract-utilities'
                                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/layouts/RootLayout.tsx:2:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/Header/index"' has no default export. Did you mean to use 'import { Header } from "/var/www/html/thedialydialectics/src/components/Header/index"' instead?

2 import Header from '@Header';
         ~~~~~~

src/layouts/RootLayout.tsx:3:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/Navbar/index"' has no default export. Did you mean to use 'import { Navbar } from "/var/www/html/thedialydialectics/src/components/Navbar/index"' instead?

3 import Navbar from '@Navbar';
         ~~~~~~

src/layouts/RootLayout.tsx:4:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/Footer/index"' has no default export. Did you mean to use 'import { Footer } from "/var/www/html/thedialydialectics/src/components/Footer/index"' instead?

4 import Footer from '@Footer';
         ~~~~~~

src/pages/_shared/DynamicArticleRoute.tsx:3:25 - error TS2307: Cannot find module './ArticlePage' or its corresponding type declarations.

3 import ArticlePage from './ArticlePage';
                          ~~~~~~~~~~~~~~~

src/pages/articlepages.tsx:6:1 - error TS6133: 'PdfViewer' is declared but its value is never read.

6 import PdfViewer from "@pdfViewer";
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/pages/articlepages.tsx:6:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/pdfViewer/index"' has no default export. Did you mean to use 'import { PdfViewer } from "/var/www/html/thedialydialectics/src/components/pdfViewer/index"' instead?

6 import PdfViewer from "@pdfViewer";
         ~~~~~~~~~

src/pages/articlepages.tsx:7:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/PageHeader/index"' has no default export. Did you mean to use 'import { PageHeader } from "/var/www/html/thedialydialectics/src/components/PageHeader/index"' instead?

7 import PageHeader from "@PageHeader";
         ~~~~~~~~~~

src/pages/articlepages.tsx:63:49 - error TS2345: Argument of type '{ readonly href: "https://thedailydialectics.com"; readonly BASE_URL: "https://thedailydialectics.com"; readonly share_url: "https://thedailydialectics.com/index"; readonly description: "In an age where truths are akin to fiction in the minds of the masses, fiction is a key component in societal control. Reprogram y...' is not assignable to parameter of type 'PageData'.
  Types of property 'media' are incompatible.
    The type 'readonly []' is 'readonly' and cannot be assigned to the mutable type 'MediaItem[]'.

63   const metadataHTML = generateFullPageMetadata(pageData, pageData.imageData).toHTML();
                                                   ~~~~~~~~

src/pages/index.tsx:5:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/MetaData/Head/MetaHead"' has no default export. Did you mean to use 'import { generateFullPageMetadata } from "/var/www/html/thedialydialectics/src/components/MetaData/Head/MetaHead"' instead?

5 import generateFullPageMetadata from "@MetaHead";
         ~~~~~~~~~~~~~~~~~~~~~~~~

src/pages/index.tsx:6:1 - error TS6133: 'PdfViewer' is declared but its value is never read.

6 import PdfViewer from "@pdfViewer";
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

src/pages/index.tsx:6:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/pdfViewer/index"' has no default export. Did you mean to use 'import { PdfViewer } from "/var/www/html/thedialydialectics/src/components/pdfViewer/index"' instead?

6 import PdfViewer from "@pdfViewer";
         ~~~~~~~~~

src/pages/index.tsx:7:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/PageHeader/index"' has no default export. Did you mean to use 'import { PageHeader } from "/var/www/html/thedialydialectics/src/components/PageHeader/index"' instead?

7 import PageHeader from "@PageHeader";
         ~~~~~~~~~~

src/pages/index.tsx:8:8 - error TS2613: Module '"/var/www/html/thedialydialectics/src/components/Body/index"' has no default export. Did you mean to use 'import { Body } from "/var/www/html/thedialydialectics/src/components/Body/index"' instead?

8 import Body from "@Body";
         ~~~~

tsconfig.json:34:1 - error TS5023: Unknown compiler option 'include'.

34 "include": ["src"],
   ~~~~~~~~~


Found 50 errors.

(solcatcher) solcatcher@abstractendeavors:/var/www/html/thedialydialectics$ 

"""
tsconfig = "/var/www/html/thedialydialectics/tsconfig.json"
ts_data = safe_read_from_json(tsconfig)
ts_data= {
  "files": [],
  "references": [
    {
      "path": "./tsconfig.app.json"
    }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": [
        "src/*"
      ],
      "@components/*": [
        "src/components/*"
      ],
      "@Navbar": [
        "src/components/Navbar"
      ],
      "@Header": [
        "src/components/Header"
      ],
      "@Footer": [
        "src/components/Footer"
      ],
      "@pdfViewer": [
        "src/components/pdfViewer"
      ],
      "@ExcelViewer": [
        "src/components/ExcelViewer"
      ],
      "@Body": [
        "src/components/Body"
      ],
      "@PageHeader": [
        "src/components/PageHeader"
      ],
      "@MetaHead": [
        "src/components/MetaData/Head/MetaHead"
      ],
      "@Sources": [
        "src/components/Sources"
      ],
      "@Social/*": [
        "src/components/Social/*"
      ],
      "@Styles/*": [
        "src/styles/*"
      ],
      "@Handles/*": [
        "src/functions/Handles/*"
      ],
      "@functions": [
        "src/functions"
      ],
      "@interfaces": [
        "src/interfaces"
      ]
    }
  }
}
def replace_in_path(string,repstring,path):
    if string != repstring:
        contents = read_from_file(path)
        contents.replace(string,repstring)
        write_to_file(contents=contents,file_path=path)
    return contents
def get_i_var(item,listObj):
    if item in listObj:
        for i,key in enumerate(listObj):
            if item == key:
                return i
    return None
paths = ts_data.get("compilerOptions",{}).get("paths")
basepath = "/var/www/html/thedialydialectics/"
error_readout = parse_tsc_output(get_errors)
for key,values in error_readout.items():
    
    paths_keys = list(paths.keys())
    paths_keys_lower = [key.lower() for key in paths_keys if key]
    for value in values:
        valvars = value.get('vars')
        path = value.get('path')
        fullpath = os.path.join(basepath,path)
        for var in valvars:
            if var.startswith('@'):
                var_lower = var.lower()
                i = get_i_var(var_lower,paths_keys_lower)
                paths_key = paths[i]
                paths_dir = paths.get(paths_key)
                paths_path = None
                paths_content=""
                if os.path.isdir(paths_dir):
                    index_path = [os.path.join(paths_dir,item) for item in os.listdir(paths_dir) if item and item.startswith('index.')]
                    if index_path:
                        paths_path = index_path[0]
                if paths_path:
                    paths_content = read_from_file(paths_path)
                get_within_quotes(paths_content,quotes=[["{","}"]])
                if 'default as' in paths_content:
                    [part for part in paths_content.split('default as')[1].split(' ') if part]
                curr_path = pathscurr_key
                if i is not None:
                    replace_in_path(var,paths_key,fullpath)            

act_var = paths[i]
