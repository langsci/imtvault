import pathlib
import collections
import re

from pyigt import IGT
from pyigt.igt import NON_OVERT_ELEMENT
from clldutils.lgr import ABBRS as lgrabbrs
from clldutils.jsonlib import load
from cldfbench import Dataset as BaseDataset

ABBRS = list(lgrabbrs.keys())
ABBRS.extend(['CONJ', 'R', 'RETRO', 'LINK', 'IFV', 'DEP', 'EXT', 'ID'])


#"\\hspace{5pt}",
"""
    {
        "ID": "7-629279",
        "bookID": 118,
        "book_title": "A grammar of Moloko",
        "categories": [
            "s"
        ],
        "citation": null,
        "clength": 36,
        "entities": [],
        "html": "<div class=\"imtblocks\">\n\t<div class=\"imtblock\">\n\t\t<div class=\"srcblock\">[à-mbaɗ=aŋ]</div>\n\t\t<div class=\"glossblock\">{3}<span class=\"sc\">s</span>+{PFV}-change={3}<span class=\"sc\">s</span>.{\\IO}</div>\n\t</div>\n\t<div class=\"imtblock\">\n\t\t<div class=\"srcblock\">\\hspace{5pt}</div>\n\t\t<div class=\"glossblock\">\\hspace{5pt}</div>\n\t</div>\n\t<div class=\"imtblock\">\n\t\t<div class=\"srcblock\">[=aka=alaj]</div>\n\t\t<div class=\"glossblock\">=on=away</div>\n\t</div>\n</div>\n",
        "imtwordsbare": [
            "{3}S+{PFV}-change={3}S.{\\IO}",
            "\\hspace{5pt}",
            "=on=away"
        ],
        "language_glottocode": "molo1266",
        "language_iso6393": "mlw",
        "language_name": "Moloko",
        "parententities": [],
        "srcwordsbare": [
            "[à-mbaɗ=aŋ]",
            "\\hspace{5pt}",
            "[=aka=alaj]"
        ],
        "trs": "He/she replied.’ (lit. he changed on away)",
        "wlength": 3
    },
"""


def clean(tex, count):
    tex = re.sub(
        r'{\\(%s)}' % '|'.join(re.escape(a) for a in ABBRS),
        lambda m: m.groups()[0],
        tex
    )
    tex = re.sub(
        r'{\\(%s)}' % '|'.join(re.escape(a.lower()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(
        r'\\(%s){}' % '|'.join(re.escape(a.lower()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(
        r'{\\(%s)}' % '|'.join(re.escape(a.capitalize()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(
        r'{([A-Z]+)}',
        lambda m: m.groups()[0],
        tex
    )
    #\gloss{cl.3sg}
    tex = re.sub(
        r'\\gloss{([a-z0-9.:-]+)}',
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(
        r'\\gloss([A-Z]+){}',
        lambda m: m.groups()[0],
        tex
    )
    tex = tex.replace('$\\emptyset$', NON_OVERT_ELEMENT)
    tex = re.sub(r'\\hspace{[^}]+}', '', tex)
    tex = re.sub(r'\\(emph|stem|bf){([^}]+)}', lambda m: m.groups()[1], tex)
    tex = tex.replace(r'\(ø\)', NON_OVERT_ELEMENT)
    tex = tex.replace(r'\gscACC', 'ACC')
    tex = tex.replace(r'\redp{}', '~')
    #\\op...\\cp{} -> (…)
    if '\\' in tex:
        count.update([tex])
    return tex


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ExampleTable', 'LGR_Conformance_Level')

        def filtered(l, c):
            return [clean(k.replace('\\t', '__t'), c) for k in l if k not in ['{}', '', '--']]

        #
        # FIXME: cobble together words: "Me-",
        #             "hu",
        #             "-u",
        #

        tex = collections.Counter()
        lgs = collections.Counter()
        seen = set()
        for p in self.dir.joinpath('extracted_examples').glob('*.json'):
            for ex in load(p):
                if ex['language_glottocode'] not in lgs:
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=ex['language_glottocode'],
                        Name=ex['language_name'] or None,
                    ))
                lgs.update([ex['language_glottocode']])
                obj = filtered(ex['srcwordsbare'], tex)
                gloss = filtered(ex['imtwordsbare'], tex)
                if not obj or (not gloss):
                    #print(ex)
                    #print(p)
                    continue
                    raise ValueError
                if any(not s for s in obj) or any(not s for s in gloss):
                    print(ex)
                    print(p)
                    #raise ValueError

                tr = ex['trs']
                igt = IGT(phrase=' '.join(obj), gloss=' '.join(gloss))
                lgr = 0
                if igt.is_valid():
                    lgr = 1
                try:
                    if igt.is_valid(strict=True):
                        lgr = 2
                except AssertionError:
                    pass
                ID = '{}-{}'.format(ex['bookID'], ex['ID']).replace('.', '_')
                if ID in seen:
                    continue
                seen.add(ID)
                args.writer.objects['ExampleTable'].append(dict(
                    ID=ID,
                    Language_ID=ex['language_glottocode'],
                    Primary_Text=' '.join(obj),
                    Analyzed_Word=obj if lgr > 0 else [],
                    Gloss=gloss if lgr > 0 else [],
                    Translated_Text=tr,
                    LGR_Conformance_Level=lgr,
                ))
        #for k, v in lgs.most_common():
        #    print(k, v)
        for k, v in tex.most_common(80):
            print(k, v)
