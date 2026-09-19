"""Curated NO/DE statutes from Lovdata public data and Gesetze im Internet.

Archive members are read in memory, never extracted onto the filesystem.
Lovdata attribution: Stiftelsen Lovdata, NLOD 2.0.
"""
import io
import re
import tarfile
import zipfile
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from src.chunking.law_chunker import StatuteSection


GERMAN_LAWS = (
    ('kschg', 'KSchG'), ('burlg', 'BUrlG'), ('arbzg', 'ArbZG'),
    ('tzbfg', 'TzBfG'), ('agg', 'AGG'), ('arbschg', 'ArbSchG'),
    ('betrvg', 'BetrVG'), ('entgfg', 'EntgFG'),
)
NORWEGIAN_LAWS = (
    ('2005-06-17-62', 'Arbeidsmiljøloven'),
    ('1988-04-29-21', 'Ferieloven'),
    ('2017-06-16-51', 'Likestillings- og diskrimineringsloven'),
    ('2012-01-27-9', 'Arbeidstvistloven'),
    ('1993-06-04-58', 'Allmenngjøringsloven'),
    ('2017-06-16-67', 'Statsansatteloven'),
)


class EuropeanLaborFetcher:
    ARCHIVE_URL = 'https://api.lovdata.no/v1/publicData/get/gjeldende-lover.tar.bz2'
    SOURCES = {'NO': ('Lovdata', 'nb'), 'DE': ('Gesetze im Internet', 'de')}

    @staticmethod
    def _download(url):
        response = requests.get(url, timeout=60, headers={'User-Agent':'MCP-LAS/1.0 (legal-source-sync)'})
        response.raise_for_status()
        return response.content

    @classmethod
    def iter_documents(cls, jurisdiction):
        if jurisdiction == 'DE':
            for slug, name in GERMAN_LAWS:
                try:
                    url = f'https://www.gesetze-im-internet.de/{slug}/'
                    with zipfile.ZipFile(io.BytesIO(cls._download(url + 'xml.zip'))) as archive:
                        members = [m for m in archive.infolist() if m.filename.endswith('.xml')]
                        if len(members) != 1 or members[0].file_size > 25_000_000:
                            raise ValueError(f'Unexpected German XML archive: {slug}')
                        yield cls.parse('DE', {'id': name, 'name': name, 'url':url}, archive.read(members[0]))
                except Exception as exc:
                    yield {'id': f'DE:{name}'}, exc
        elif jurisdiction == 'NO':
            with tarfile.open(fileobj=io.BytesIO(cls._download(cls.ARCHIVE_URL)), mode='r:bz2') as archive:
                for law_id, name in NORWEGIAN_LAWS:
                    try:
                        year, month, day, number = law_id.split('-')
                        member = archive.getmember(f'nl/nl-{year}{month}{day}-{int(number):03d}.xml')
                        if not member.isfile() or member.size > 25_000_000:
                            raise ValueError(f'Unexpected Lovdata member: {law_id}')
                        with archive.extractfile(member) as stream:
                            yield cls.parse('NO', {'id':law_id, 'name':name,
                                'url':f'https://lovdata.no/dokument/NL/lov/{law_id}'}, stream.read().decode('utf-8'))
                    except Exception as exc:
                        yield {'id': f'NO:{law_id}'}, exc
        else:
            raise ValueError('Only NO and DE are supported by this adapter')

    @classmethod
    def parse(cls, jurisdiction, document, payload):
        source, language = cls.SOURCES[jurisdiction]
        sections = []
        seen = set()

        def append(number, title, content, chapter=None):
            number = re.sub(r'\s+', ' ', number.strip().lower())
            if number in seen:
                raise ValueError(f'Duplicate section {number} in {document["id"]}')
            seen.add(number)
            # Repealed headings with no normative text remain out of the index.
            if not content.strip():
                return
            safe = re.sub(r'[^\w-]+', '-', document['id'].lower())
            sections.append(StatuteSection(
                id=f'{jurisdiction.lower()}-{safe}_s{number}', statute_id=document['id'],
                statute_short=document['name'], chapter=chapter, section_number=number,
                section_title=title or None, content=content, raw_text=f'§ {number} {title}\n{content}',
                keywords=[document['name'].lower(), number, jurisdiction.lower()],
            ))

        if jurisdiction == 'DE':
            root = ET.fromstring(payload)
            for norm in root.findall('norm'):
                label = norm.findtext('metadaten/enbez', '')
                match = re.fullmatch(r'§\s*(\d+[a-z]?)', label.strip(), re.I)
                if not match:
                    continue
                content = norm.find('textdaten/text/Content')
                text = '\n'.join(' '.join(p.itertext()).strip() for p in content) if content is not None else ''
                title_node = norm.find('metadaten/titel')
                title = ''.join(title_node.itertext()) if title_node is not None else ''
                append(match.group(1), title, text)
        else:
            soup = BeautifulSoup(payload, 'html.parser')
            for node in soup.select('main.documentBody article.legalArticle'):
                label = node.select_one('.legalArticleValue')
                if label is None:
                    raise ValueError('Missing Lovdata paragraph label')
                # Treaty appendices use Art labels, outside this statute-section catalog.
                if label.get_text(' ', strip=True).startswith('Art'):
                    continue
                number = label.get_text(' ', strip=True).removeprefix('§').strip().rstrip('.')
                if not re.fullmatch(r'\d+(?:\s*[a-z])?(?:-\d+(?:\s*[a-z])?)?', number, re.I):
                    raise ValueError(f'Unexpected Lovdata paragraph label: {number}')
                title = node.select_one('.legalArticleTitle')
                title_text = title.get_text(' ',strip=True) if title else ''
                paragraphs = node.find_all('article', class_=['legalP', 'numberedLegalP', 'defaultP'], recursive=False)
                text = '\n'.join(p.get_text(' ',strip=True) for p in paragraphs)
                chapter = number.split('-')[0].lower() if '-' in number else None
                append(number, title_text, text, chapter)
        if not sections:
            raise ValueError(f'No sections parsed for {jurisdiction}/{document["id"]}')
        metadata = {'id': f'{jurisdiction}:{document["id"]}', 'statute_id':document['id'],
            'short_name':document['name'], 'title':document['name'], 'source':source,
            'source_url':document['url'], 'jurisdiction':jurisdiction, 'language':language,
            'total_sections':len(sections)}
        if jurisdiction == 'NO':
            metadata['license'] = 'NLOD-2.0'
            metadata['attribution'] = 'Stiftelsen Lovdata'
        return metadata, sections
