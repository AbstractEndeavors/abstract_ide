from abstract_utilities import *
get_docs = """src/components/CssVariablesControl/CssVariablesControl.tsx(2,27): error TS1484: 'ChangeEvent' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/CssVariablesControl/CssVariablesControl.tsx(4,9): error TS1484: 'CssVariable' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/MetaData/Head/MetaHead.tsx(1,10): error TS1484: 'ImageData' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/MetaData/Head/MetaHead.tsx(1,21): error TS1484: 'PageData' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/MetaData/Head/meta_image.tsx(1,10): error TS1484: 'ImageData' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/MetaData/Head/meta_image.tsx(21,11): error TS6133: 'baseUrl' is declared but its value is never read.
src/components/Navbar/Navbar.tsx(2,18): error TS2307: Cannot find module 'next/link' or its corresponding type declarations.
src/components/Navbar/Navbar.tsx(3,29): error TS2307: Cannot find module 'next/navigation' or its corresponding type declarations.
src/components/Navbar/Navbars.tsx(3,1): error TS6133: 'Link' is declared but its value is never read.
src/components/Navbar/Navbars.tsx(3,18): error TS2307: Cannot find module 'next/link' or its corresponding type declarations.
src/components/Navbar/Navbars.tsx(4,29): error TS2307: Cannot find module 'next/navigation' or its corresponding type declarations.
src/components/Navbar/Navbars.tsx(12,54): error TS6133: 'theme' is declared but its value is never read.
src/components/Navbar/Navbars.tsx(39,41): error TS6133: 'index' is declared but its value is never read.
src/components/PageHeader/PageHeader.tsx(1,19): error TS2307: Cannot find module 'next/image' or its corresponding type declarations.
src/components/PageHeader/PageHeader.tsx(2,10): error TS1484: 'PageData' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/Social/Facebook/Share/Button.tsx(2,9): error TS1484: 'SocialShareButtonProps' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/Social/Props/ShareButton.tsx(2,10): error TS2724: '"@interfaces"' has no exported member named 'SocialShareUrlButtonProps'. Did you mean 'SocialShareButtonProps'?
src/components/Social/Props/ShareButton.tsx(11,3): error TS2339: Property 'platform' does not exist on type 'ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(12,3): error TS2339: Property 'text' does not exist on type 'ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(13,3): error TS2339: Property 'url' does not exist on type 'ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(14,3): error TS2339: Property 'via' does not exist on type 'ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(15,3): error TS2339: Property 'hashtags' does not exist on type 'ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(42,13): error TS2322: Type '{ key: string; platform: string; text: any; url: any; via: any; hashtags: any; }' is not assignable to type 'IntrinsicAttributes & ShareButtonProps'.
  Property 'platform' does not exist on type 'IntrinsicAttributes & ShareButtonProps'.
src/components/Social/Props/ShareButton.tsx(54,13): error TS2322: Type '{ key: string; platform: string; text: any; url: any; via: any; hashtags: any; }' is not assignable to type 'IntrinsicAttributes & ShareButtonProps'.
  Property 'platform' does not exist on type 'IntrinsicAttributes & ShareButtonProps'.
src/components/Social/X/Share/Button.tsx(2,9): error TS1484: 'SocialShareButtonProps' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/SourceEditor/SourceEditor.tsx(20,11): error TS6196: 'MetadataEditorProps' is declared but never used.
src/components/Sources/Sources.tsx(3,9): error TS1484: 'MediaSource' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/components/pdfViewer/pdfViewer.tsx(4,19): error TS2307: Cannot find module 'next/image' or its corresponding type declarations.
src/components/pdfViewer/pdfViewer.tsx(6,10): error TS1484: 'FormatType' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/functions/content_parser.tsx(3,1): error TS6192: All imports in import declaration are unused.
src/functions/content_parser.tsx(75,38): error TS6133: 'meta' is declared but its value is never read.
src/functions/content_parser.tsx(75,49): error TS6133: 'filename' is declared but its value is never read.
src/functions/content_parser.tsx(99,38): error TS6133: 'meta' is declared but its value is never read.
src/functions/content_parser.tsx(99,49): error TS6133: 'filename' is declared but its value is never read.
src/functions/content_parser.tsx(112,45): error TS6133: 'filename' is declared but its value is never read.
src/functions/content_parser.tsx(115,39): error TS6133: 'jsonPath' is declared but its value is never read.
src/functions/content_parser.tsx(152,21): error TS6133: 'directory' is declared but its value is never read.
src/functions/content_parser.tsx(152,73): error TS6133: 'background' is declared but its value is never read.
src/functions/content_parser.tsx(233,54): error TS6133: 'filename' is declared but its value is never read.
src/functions/content_parser.tsx(270,19): error TS6133: 'style' is declared but its value is never read.
src/functions/content_parser.tsx(271,19): error TS6133: 'loading' is declared but its value is never read.
src/functions/index.ts(2,1): error TS2308: Module './content_parser' has already exported a member named 'build_content'. Consider explicitly re-exporting to resolve the ambiguity.
src/functions/index.ts(4,1): error TS2308: Module './functions.server' has already exported a member named 'get_filename'. Consider explicitly re-exporting to resolve the ambiguity.
src/functions/path_utils_client.ts(3,49): error TS2307: Cannot find module '@putkoff/abstract-utilities' or its corresponding type declarations.
src/functions/tdd_fetch_functions.ts(1,9): error TS1484: 'Source' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
src/layouts/RootLayout.tsx(2,8): error TS2613: Module '"/var/www/TDD/my-app/src/components/Header/index"' has no default export. Did you mean to use 'import { Header } from "/var/www/TDD/my-app/src/components/Header/index"' instead?
src/layouts/RootLayout.tsx(3,8): error TS2613: Module '"/var/www/TDD/my-app/src/components/Navbar/index"' has no default export. Did you mean to use 'import { Navbar } from "/var/www/TDD/my-app/src/components/Navbar/index"' instead?
src/layouts/RootLayout.tsx(4,8): error TS2613: Module '"/var/www/TDD/my-app/src/components/Footer/index"' has no default export. Did you mean to use 'import { Footer } from "/var/www/TDD/my-app/src/components/Footer/index"' instead?
src/pages/_shared/DynamicArticleRoute.tsx(3,25): error TS2307: Cannot find module './ArticlePage' or its corresponding type declarations.
src/pages/articlepages.tsx(6,1): error TS6133: 'PdfViewer' is declared but its value is never read.
src/pages/articlepages.tsx(63,49): error TS2345: Argument of type '{ readonly href: "https://thedailydialectics.com"; readonly BASE_URL: "https://thedailydialectics.com"; readonly share_url: "https://thedailydialectics.com/index"; readonly description: "In an age where truths are akin to fiction in the minds of the masses, fiction is a key component in societal control. Reprogram y...' is not assignable to parameter of type 'PageData'.
  Types of property 'media' are incompatible.
    The type 'readonly []' is 'readonly' and cannot be assigned to the mutable type 'MediaItem[]'.
src/pages/articlepages.tsx(121,20): error TS2322: Type '{ readonly href: "https://thedailydialectics.com"; readonly BASE_URL: "https://thedailydialectics.com"; readonly share_url: "https://thedailydialectics.com/index"; readonly description: "In an age where truths are akin to fiction in the minds of the masses, fiction is a key component in societal control. Reprogram y...' is not assignable to type 'PageData'.
  Types of property 'media' are incompatible.
    The type 'readonly []' is 'readonly' and cannot be assigned to the mutable type 'MediaItem[]'.
src/pages/index.tsx(6,1): error TS6133: 'PdfViewer' is declared but its value is never read.
src/pages/index.tsx(63,49): error TS2345: Argument of type '{ readonly href: "https://thedailydialectics.com"; readonly BASE_URL: "https://thedailydialectics.com"; readonly share_url: "https://thedailydialectics.com/index"; readonly description: "In an age where truths are akin to fiction in the minds of the masses, fiction is a key component in societal control. Reprogram y...' is not assignable to parameter of type 'PageData'.
  Types of property 'media' are incompatible.
    The type 'readonly []' is 'readonly' and cannot be assigned to the mutable type 'MediaItem[]'.
src/pages/index.tsx(121,20): error TS2322: Type '{ readonly href: "https://thedailydialectics.com"; readonly BASE_URL: "https://thedailydialectics.com"; readonly share_url: "https://thedailydialectics.com/index"; readonly description: "In an age where truths are akin to fiction in the minds of the masses, fiction is a key component in societal control. Reprogram y...' is not assignable to type 'PageData'.
  Types of property 'media' are incompatible.
    The type 'readonly []' is 'readonly' and cannot be assigned to the mutable type 'MediaItem[]'.
error Command failed with exit code 2.
info Visit https://yarnpkg.com/en/docs/cli/run for documentation about this command.


[build] exited with code 2""".split('\n')
root = '/var/www/TDD/my-app'
varsJs = {}
def safePlit(*steps):
    """
    Chainable safe split utility.

    Each step is a list/tuple of: [source_or_None, sep_or_None, index_or_None]
      - source_or_None: string to operate on, or None to use the previous output
      - sep_or_None: separator for str.split(); if None, don't split
      - index_or_None: which part to pick; if None, return the full list

    Returns a string or list depending on the last step.
    """
    out = None

    for step in steps:
        # Normalize step to 3 items
        if not isinstance(step, (list, tuple)) or len(step) != 3:
            raise ValueError(f"Each step must be a 3-item list/tuple, got: {step}")

        src, sep, idx = step

        # Resolve source
        s = out if src is None else src
        if s is None:
            return ""  # nothing to work with

        # If no separator: optionally index a list, else pass-through
        if sep is None:
            if idx is None:
                out = s
            else:
                if isinstance(s, list):
                    i = idx
                    if isinstance(i, int):
                        if i < 0:
                            i += len(s)
                        out = s[i] if 0 <= i < len(s) else ""
                    else:
                        out = s  # invalid idx type → pass-through
                else:
                    out = s  # not a list → pass-through
            continue

        # Perform split
        parts = str(s).split(sep)

        # Return full list if idx is None
        if idx is None:
            out = parts
            continue

        # Pick an index (support negatives)
        if isinstance(idx, int):
            i = idx
            if i < 0:
                i += len(parts)
            out = parts[i] if 0 <= i < len(parts) else ""
        else:
            # Non-int index → safest is to return the whole list
            out = parts

    return out

for splitdoc in get_docs:
    splitdoc_spl = safePlit([splitdoc,'(',0])
    file_path = os.path.join(root,splitdoc_spl)
    lines = safePlit([splitdoc, '(', 1], [None, ')', 0], [None, ',', None])
    error = safePlit([splitdoc, ':', 1])
    readout = safePlit([splitdoc, ':', -1])
    varType = safePlit([splitdoc, "'", 0])
    variableremaining = safePlit([splitdoc, "'", None])
    variable = safePlit([variableremaining, None, 1])
    remaining = safePlit([variableremaining, None, 2])
    variable2 = safePlit([variableremaining, None, 3])
    remaining2 = safePlit([variableremaining, None, -1])
    
    keyVars = """file_path,lines,error,readout,readout,variable,variable2,varType,remaining,remaining2""".split(',')
    variables = [file_path,lines,error,readout,readout,variable,variable2,varType,remaining,remaining2]
    if file_path not in varsJs:
        varsJs[file_path] = []
    varsJs[file_path].append({})
    for i,varVar in enumerate(variables):
        varsJs[file_path][-1][keyVars[i]] =eatAll(varVar,[',','(',')',' ','"',"'"])

