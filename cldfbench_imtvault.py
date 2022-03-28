import pathlib
import collections
import re

from pyigt import IGT
from pyigt.igt import NON_OVERT_ELEMENT, LGRConformance
from pyigt.lgrmorphemes import MORPHEME_SEPARATORS
from clldutils.lgr import ABBRS as lgrabbrs
from clldutils.jsonlib import load
from cldfbench import Dataset as BaseDataset

ABBRS = list(lgrabbrs.keys())
ABBRS.extend([
    'FEM',
    'CL',
    'COMP',
    'CONN',
    'CONJ',
    'DIM',
    'PRAG',
    'R', 'RETRO', 'LINK', 'IFV', 'DEP', 'EXT', 'ID', 'CONTR', 'IO', 'DO', 'TNS'])


def clean(tex, count):
    tex = re.sub(  # {\ABBR}
        r'{\\(%s)}' % '|'.join(re.escape(a) for a in ABBRS),
        lambda m: m.groups()[0],
        tex
    )
    tex = re.sub(  # {\abbr}
        r'{\\(%s)}' % '|'.join(re.escape(a.lower()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(  # \abbr{}
        r'\\(%s){}' % '|'.join(re.escape(a.lower()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(  # {\Abbr}
        r'{\\(%s)}' % '|'.join(re.escape(a.capitalize()) for a in ABBRS),
        lambda m: m.groups()[0].upper(),
        tex
    )
    tex = re.sub(  # {ABBR}
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
    tex = re.sub(r'\\(mc){([^}]+)}', lambda m: m.groups()[1].upper(), tex)
    tex = tex.replace(r'\(ø\)', NON_OVERT_ELEMENT)
    tex = re.sub(r'\\gsc([A-Z]+)', lambda m: m.groups()[0], tex)
    tex = tex.replace(r'\redp{}', '~')
    tex = tex.replace('${\\Rightarrow}$', '→')
    tex = tex.replace(r'{\USSmaller}', '<')
    tex = tex.replace(r'{\USGreater}', '>')
    tex = tex.replace(r'\Third{}', '3')
    tex = tex.replace(r'\Tsg{}', '3SG')
    tex = tex.replace(r'\Tpl{}', '3PL')
    tex = tex.replace(r'\Third.', '3.')
    tex = tex.replace(r'\Third>', '3>')
    tex = tex.replace(r'\Tsg.', '3SG.')
    tex = tex.replace(r'\squish', '')
    tex = tex.replace('__tld{}', '~')
    #\\op...\\cp{} -> (…)
    if '\\' in tex:
        count.update([tex])
    return tex


def recombine(l):
    chunk = []
    for c in l:
        if not c:
            continue
        if c[0] in MORPHEME_SEPARATORS or (chunk and chunk[-1][-1] in MORPHEME_SEPARATORS):
            chunk.append(c)
        else:
            if chunk:
                yield ''.join(chunk)
            chunk = [c]
    if chunk:
        yield ''.join(chunk)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component(
            'LanguageTable',
            {
                'name': 'Examples_Count',
                'datatype': 'integer',
            }
        )
        args.writer.cldf.add_component(
            'ExampleTable',
            {
                'name': 'LGR_Conformance_Level',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(str(l)) for l in LGRConformance)}
            },
            {
                'name': 'Abbreviations',
                'datatype': 'json',
            }
        )

        def filtered(l, c):
            return list(recombine([clean(k.replace('\\t', '__t'), c) for k in l if k not in ['{}', '', '--']]))

        tex = collections.Counter()
        lgs = collections.Counter()
        seen = set()
        for p in self.dir.joinpath('extracted_examples').glob('*.json'):
            for ex in load(p):
                if ex['language_glottocode'] not in lgs:
                    glang = None
                    if ex['language_glottocode'] != 'und':
                        glang = args.glottolog.api.cached_languoids[ex['language_glottocode']]
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=ex['language_glottocode'],
                        Name=ex['language_name'] or (glang.name if glang else 'Undefined'),
                        Glottocode=glang.id if glang else None,
                        Latitude=glang.latitude if glang else None,
                        Longitude=glang.longitude if glang else None,
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
                    raise ValueError

                tr = ex['trs']
                igt = IGT(phrase=' '.join(obj), gloss=' '.join(gloss))
                conformance = igt.conformance
                ID = '{}-{}'.format(ex['bookID'], ex['ID']).replace('.', '_')
                if ID in seen:
                    print('+++dup+++', p.name, ID)
                    continue
                seen.add(ID)
                args.writer.objects['ExampleTable'].append(dict(
                    ID=ID,
                    Language_ID=ex['language_glottocode'],
                    Primary_Text=' '.join(obj),
                    Analyzed_Word=obj if conformance > LGRConformance.UNALIGNED else [],
                    Gloss=gloss if conformance > LGRConformance.UNALIGNED else [],
                    Translated_Text=tr,
                    LGR_Conformance_Level=str(conformance),
                    Abbreviations=igt.gloss_abbrs if conformance == LGRConformance.MORPHEME_ALIGNED else {},
                ))
        for lg in args.writer.objects['LanguageTable']:
            if lg['ID'] != 'und':
                lg['Examples_Count'] = lgs.get(lg['ID'], 0)
        #for k, v in lgs.most_common():
        #    print(k, v)
        #for k, v in tex.most_common(100):
        #    print(k, v)
