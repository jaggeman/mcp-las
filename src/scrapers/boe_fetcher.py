"""Bounded Spanish labour-law catalogue from BOE's consolidated-text API.

Only numbered articles are indexed, not supplementary/transitional provisions.
Consolidated texts are informational; consult the original official publication.
"""
import datetime
import re
import xml.etree.ElementTree as ET
import requests
from src.chunking.law_chunker import StatuteSection

SPANISH_LAWS = (
    ('BOE-A-2015-11430', 'Estatuto de los Trabajadores'),
    ('BOE-A-1995-24292', 'Prevención de Riesgos Laborales'),
    ('BOE-A-1985-16660', 'Libertad Sindical'),
    ('BOE-A-2007-6115', 'Igualdad efectiva de mujeres y hombres'),
    ('BOE-A-2021-11472', 'Trabajo a distancia'),
)


class BoeFetcher:
    @staticmethod
    def fetch(identifier):
        url = f'https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{identifier}/texto'
        with requests.get(url, headers={'Accept': 'application/xml'}, timeout=(10, 60), stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError('BOE response too large')
            return bytes(data)

    @classmethod
    def iter_documents(cls):
        for identifier, title in SPANISH_LAWS:
            try:
                yield cls.parse(identifier, title, cls.fetch(identifier))
            except Exception as exc:
                yield {'id': f'ES:{identifier}'}, exc

    @staticmethod
    def parse(identifier, title, payload, as_of=None):
        if isinstance(payload, str): payload = payload.encode('utf-8')
        if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
            raise ValueError('Unexpected XML declaration')
        root = ET.fromstring(payload)
        if root.findtext('status/code') != '200':
            raise ValueError('BOE API did not return success')
        today = (as_of or datetime.datetime.now(datetime.timezone.utc).date()).strftime('%Y%m%d')
        sections, seen = [], set()
        for block in root.findall('.//texto/bloque'):
            label = block.get('titulo', '')
            normalized = label.strip().rstrip('.').lower()
            written = ['primero', 'segundo', 'tercero', 'cuarto', 'quinto', 'sexto',
                       'séptimo', 'octavo', 'noveno', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince']
            for i, word in enumerate(written, 1):
                if normalized == f'artículo {word}': normalized = f'artículo {i}'
            match = re.fullmatch(r'artículo\s+(\d+(?:\s+(?:bis|ter|quater))?)', normalized, re.I)
            if not match:
                continue
            number = match.group(1).lower()
            if number in seen: raise ValueError(f'Duplicate BOE article {number}')
            seen.add(number)
            versions = []
            for v in block.findall('version'):
                published = v.get('fecha_publicacion', '')
                effective = v.get('fecha_vigencia') or published
                if not re.fullmatch(r'\d{8}', effective) or not re.fullmatch(r'\d{8}', published):
                    raise ValueError('Missing BOE version date')
                datetime.datetime.strptime(effective, '%Y%m%d')
                datetime.datetime.strptime(published, '%Y%m%d')
                if effective <= today and published <= today:
                    versions.append((effective, published, v))
            if not versions: continue
            version = max(versions, key=lambda row: row[:2])[2]
            paragraphs = [' '.join(''.join(child.itertext()).split()) for child in version]
            body = paragraphs[1:] if paragraphs and paragraphs[0].startswith('Artículo ') else paragraphs
            if not body or re.fullmatch(r'[\s().]*(?:Derogad[oa]|Suprimid[oa])[\s().]*', ' '.join(body), re.I):
                continue
            content = '\n'.join(paragraphs)
            sections.append(StatuteSection(
                id=f'es-{identifier.lower()}_s{number.replace(" ", "-")}',
                statute_id=identifier, statute_short=title, section_number=number,
                section_title=label, content=content, raw_text=content,
                keywords=[title.lower(), number, 'es'],
            ))
        if not sections: raise ValueError('No active BOE articles parsed')
        return {'id': f'ES:{identifier}', 'statute_id': identifier, 'short_name': title,
                'title': title, 'jurisdiction': 'ES', 'language': 'es', 'source': 'BOE',
                'source_url': f'https://www.boe.es/buscar/act.php?id={identifier}',
                'attribution': 'Agencia Estatal Boletín Oficial del Estado; texto consolidado informativo, sin valor jurídico oficial.',
                'total_sections': len(sections)}, sections
