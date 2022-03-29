import re
import math
import pathlib
import collections
import urllib.request

from tqdm import tqdm
from pyigt import IGT
from pyigt.igt import NON_OVERT_ELEMENT, LGRConformance
from pyigt.lgrmorphemes import MORPHEME_SEPARATORS
from clldutils.lgr import ABBRS as lgrabbrs
from clldutils.jsonlib import load
from cldfbench import Dataset as BaseDataset
from bs4 import BeautifulSoup as bs

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
META_LANGS = {
    'eng',
    'fra',
    'spa',
    'cmn',
    'por',
    'deu',
}


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

def clean_abbr(k):
    # 1, 2, 3
    # 1/2/3
    # 1,2,3
    # 1, 2, 3,
    # I,II,III
    k = re.sub(r'{\\(sc|SC){([a-z]+)}}', lambda m: m.groups()[1], k)
    k = re.sub(r'{\\(sc|SC)\s+([a-z]+)}', lambda m: m.groups()[1], k)
    k = re.sub(r'^{([A-Z]+)}$', lambda m: m.groups()[0], k)
    k = re.sub(r'^\\([A-Z]+)({})?$', lambda m: m.groups()[0], k)
    k = re.sub(r'^([A-Z]+)({})?$', lambda m: m.groups()[0], k)
    #k = k.replace('\\', '').replace('{', '').replace('}', '')
    k = k.upper()
    if re.fullmatch('[A-Z]+', k):
        return k


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "imtvault"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        def get_bibtex(book_id):
            res = urllib.request.urlopen('https://langsci-press.org/catalog/book/{}'.format(book_id))
            soup = bs(res.read().decode('utf8'), features='html.parser')
            for button in soup.find_all('button'):
                if button.text == 'Copy BibTeX':
                    res = button['onclick'].replace("copyToClipboard('", '').replace("')", '').replace('<br>', '\n')
                    return re.sub(r'@([a-z]+){([^,]+),', lambda m: '@{}{{lsp{},'.format(m.groups()[0], str(book_id)), res)

        missing = set()
        abbrs = collections.Counter()
        for p in tqdm(list(self.dir.joinpath('extracted_examples').glob('*.json'))):
            for ex in load(p):
                #abbrs.update([clean_abbr(k) for k in (ex['abbrkey'] or {}).keys() if not re.fullmatch('[0-9A-Z]+', clean_abbr(k))])
                #continue
                op = self.etc_dir / 'bibtex' / '{}.bib'.format(ex['book_ID'])
                if not op.exists() and (ex['book_ID'] not in missing):
                    bibtex = get_bibtex(ex['book_ID'])
                    if bibtex:
                        op.write_text(bibtex, encoding='utf8')
                    else:
                        missing.add(ex['book_ID'])
        for k, v in abbrs.most_common():
            print(k, v)

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component(
            'LanguageTable',
            {
                'name': 'Examples_Count',
                'datatype': 'integer',
            },
            {
                'name': 'Examples_Count_Log',
                'datatype': 'number',
            },
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
            },
            {
                'name': 'Source',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source',
                'separator': ';'
            },
        )

        def filtered(l, c):
            return list(recombine([clean(k.replace('\\t', '__t'), c) for k in l if k not in ['{}', '', '--']]))

        def fix_bibtex(s):
            res, doi = [], False
            for line in s.split('\n'):
                if line.strip().startswith('doi'):
                    if doi:
                        continue
                    else:
                        doi = True
                if 'author' in line:
                    line = line.replace('and ', ' and ')
                res.append(line)
            return '\n'.join(res)

        def get_abbrs(d):
            res = {}
            for k, v in (d or {}).items():
                k = clean_abbr(k)
                if k:
                    res[k] = v
            return res

        with_source = set()
        for p in sorted(self.etc_dir.joinpath('bibtex').glob('*.bib'), key=lambda pp: int(pp.stem)):
            with_source.add(p.stem)
            args.writer.cldf.sources.add(fix_bibtex(p.read_text(encoding='utf8')))

        tex = collections.Counter()
        lgs = collections.Counter()
        mlgs = {}
        seen = set()
        for p in self.dir.joinpath('extracted_examples').glob('*.json'):
            fname = re.sub('store-[0-9]+-', '', p.stem) + 'tex'
            for ex in load(p):
                # FIXME:
                # - abbrkey
                #
                try:
                    if str(ex['book_ID']) not in with_source:
                        continue  # Either an unpublished or a superseded book.
                except:
                    print(p)
                    print(ex)
                    raise

                obj = filtered(ex['srcwordsbare'], tex)
                gloss = filtered(ex['imtwordsbare'], tex)
                if not (obj and gloss):
                    assert obj == gloss == []
                    continue  # No primary text or gloss.
                assert all(s for s in obj) and all(s for s in gloss)

                if ex['book_metalanguage'] and ex['book_metalanguage'] not in mlgs:
                    glang = args.glottolog.api.cached_languoids[args.glottolog.api.glottocode_by_iso[ex['book_metalanguage']]]
                    mlgs[ex['book_metalanguage']] = glang.id
                    args.writer.objects['LanguageTable'].append(dict(
                        ID=glang.id,
                        Name=glang.name,
                        Glottocode=glang.id,
                        Latitude=glang.latitude,
                        Longitude=glang.longitude,
                    ))

                if ex['language_glottocode'] not in lgs:
                    glang = None
                    if ex['language_glottocode'] != 'und':
                        glang = args.glottolog.api.cached_languoids[ex['language_glottocode']]
                    if not glang or (glang.iso not in mlgs):
                        args.writer.objects['LanguageTable'].append(dict(
                            ID=ex['language_glottocode'],
                            Name=ex['language_name'] or (glang.name if glang else 'Undefined'),
                            Glottocode=glang.id if glang else None,
                            Latitude=glang.latitude if glang else None,
                            Longitude=glang.longitude if glang else None,
                        ))
                    if glang and glang.iso:
                        mlgs[glang.iso] = glang.id

                lgs.update([ex['language_glottocode']])
                tr = ex['trs']
                igt = IGT(
                    phrase=' '.join(obj),
                    gloss=' '.join(gloss),
                    abbrs=get_abbrs(ex['abbrkey']),
                )
                conformance = igt.conformance
                ID = '{}-{}'.format(ex['book_ID'], ex['ID']).replace('.', '_')
                if ID in seen:
                    #print('+++dup+++', p.name, ID)
                    continue
                seen.add(ID)
                args.writer.objects['ExampleTable'].append(dict(
                    ID=ID,
                    Language_ID=ex['language_glottocode'],
                    Meta_Language_ID=mlgs.get(ex['book_metalanguage']),
                    Primary_Text=' '.join(obj),
                    Analyzed_Word=obj if conformance > LGRConformance.UNALIGNED else [],
                    Gloss=gloss if conformance > LGRConformance.UNALIGNED else [],
                    Translated_Text=tr,
                    LGR_Conformance_Level=str(conformance),
                    Abbreviations=igt.gloss_abbrs if conformance == LGRConformance.MORPHEME_ALIGNED else {},
                    Source=['lsp{}'.format(ex['book_ID'])]
                ))
        for lg in args.writer.objects['LanguageTable']:
            if lg['ID'] != 'und':
                lg['Examples_Count'] = lgs.get(lg['ID'], 0)
                lg['Examples_Count_Log'] = math.log(lgs.get(lg['ID'], 1))
        #for k, v in lgs.most_common():
        #    print(k, v)
        #for k, v in tex.most_common(100):
        #    print(k, v)
